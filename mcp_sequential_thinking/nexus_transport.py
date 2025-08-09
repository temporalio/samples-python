"""
Simple Nexus transport for MCP that routes messages through Temporal Nexus
instead of stdio/http transports.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Optional

import mcp.types as types
from mcp.client.session import ClientSession
from mcp.shared.message import SessionMessage


class AsyncioStreamAdapter:
    """Makes asyncio.Queue look like a stream for MCP compatibility."""

    def __init__(self, queue: asyncio.Queue):
        self.queue = queue
        self._closed = False

    async def send(self, item: SessionMessage) -> None:
        if self._closed:
            raise RuntimeError("Stream is closed")
        await self.queue.put(item)

    async def receive(self) -> SessionMessage:
        if self._closed:
            raise RuntimeError("Stream is closed")
        return await self.queue.get()

    def __aiter__(self):
        return self

    async def __anext__(self) -> SessionMessage:
        if self._closed:
            raise StopAsyncIteration
        item = await self.queue.get()
        if item is None:  # Sentinel for stream end
            self._closed = True
            raise StopAsyncIteration
        return item

    async def aclose(self) -> None:
        self._closed = True
        # Signal any waiters
        try:
            self.queue.put_nowait(None)
        except asyncio.QueueFull:
            pass


class NexusMCPTransport:
    """Routes MCP protocol messages through Temporal Nexus."""

    def __init__(self, nexus_client, operation_token: str):
        self.nexus_client = nexus_client
        self.operation_token = operation_token

    @asynccontextmanager
    async def connect(self):
        """Create bidirectional streams that route through Nexus."""
        # Create queues for communication
        read_queue = asyncio.Queue()
        write_queue = asyncio.Queue()

        # Wrap in stream adapters
        read_stream = AsyncioStreamAdapter(read_queue)
        write_stream = AsyncioStreamAdapter(write_queue)

        # Task to route messages
        async def message_router():
            try:
                while True:
                    msg = await write_queue.get()
                    if msg is None:  # Shutdown signal
                        break

                    # Route to Nexus and put response back
                    response = await self._route_to_nexus(msg)
                    if response:
                        await read_queue.put(response)
            finally:
                await read_queue.put(None)  # EOF signal

        router_task = asyncio.create_task(message_router())

        try:
            yield read_stream, write_stream
        finally:
            await write_stream.aclose()
            router_task.cancel()
            try:
                await router_task
            except asyncio.CancelledError:
                pass

    async def _route_to_nexus(self, msg: SessionMessage) -> Optional[SessionMessage]:
        """Route MCP message to appropriate Nexus operation."""
        message = msg.message
        if not isinstance(message.root, types.JSONRPCRequest):
            return None

        request = message.root

        # Handle initialize (required by MCP protocol)
        if request.method == "initialize":
            result = types.InitializeResult(
                protocolVersion="2024-11-15",
                capabilities=types.ServerCapabilities(tools=types.ToolsCapability()),
                serverInfo=types.Implementation(
                    name="nexus-mcp-server", version="0.1.0"
                ),
            )

        # Handle tools/list
        elif request.method == "tools/list":
            from .mcp_server.nexus_service import ListToolsInput, MCPServerNexusService

            result = await self.nexus_client.execute_operation(
                MCPServerNexusService.list_tools,
                ListToolsInput(
                    operation_token=self.operation_token,
                    request=types.ListToolsRequest(method="tools/list"),
                ),
            )

        # Handle tools/call
        elif request.method == "tools/call":
            from .mcp_server.nexus_service import CallToolInput, MCPServerNexusService

            params = request.params
            if isinstance(params, dict) and "name" in params:
                result = await self.nexus_client.execute_operation(
                    MCPServerNexusService.call_tool,
                    CallToolInput(
                        operation_token=self.operation_token,
                        request=types.CallToolRequest(
                            method="tools/call",
                            params=types.CallToolRequestParams(
                                name=params["name"],
                                arguments=params.get("arguments", {}),
                            ),
                        ),
                    ),
                )
            else:
                result = types.ErrorData(
                    code=types.INVALID_PARAMS, message="Missing tool name"
                )

        else:
            result = types.ErrorData(
                code=types.METHOD_NOT_FOUND, message=f"Unknown method: {request.method}"
            )

        # Wrap in JSON-RPC response
        response = types.JSONRPCResponse(
            jsonrpc="2.0",
            id=request.id,
            result=result if not isinstance(result, types.ErrorData) else None,
            error=result if isinstance(result, types.ErrorData) else None,
        )

        return SessionMessage(types.JSONRPCMessage(root=response))


@asynccontextmanager
async def create_nexus_mcp_client(nexus_client, operation_token: str):
    """Create an MCP client that routes through Nexus instead of stdio."""
    transport = NexusMCPTransport(nexus_client, operation_token)

    async with transport.connect() as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session
