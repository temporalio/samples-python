"""
Nexus transport for MCP that uses the standard MCP ClientSession.
This approach stays close to the MCP Python SDK by implementing a custom transport.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Optional

import mcp.types as types
from mcp.client.session import ClientSession
from mcp.shared.message import SessionMessage


class NexusTransport:
    """
    A transport that routes MCP messages through Temporal Nexus.
    Provides the same interface as stdio_client but uses Nexus operations.
    """

    def __init__(self, nexus_client, operation_token: str):
        self.nexus_client = nexus_client
        self.operation_token = operation_token

    @asynccontextmanager
    async def connect(self):
        """
        Create bidirectional streams that route through Nexus.
        Returns (read_stream, write_stream) like stdio_client.
        """
        from temporalio import workflow

        workflow.logger.info("NexusTransport.connect() called")

        # Create asyncio queues for communication
        read_queue = asyncio.Queue()
        write_queue = asyncio.Queue()

        # Create stream adapters
        read_stream = AsyncioQueueStream(read_queue)
        write_stream = AsyncioQueueStream(write_queue)

        # Task to route messages
        async def message_router():
            workflow.logger.info("Message router started")
            try:
                while True:
                    # Get message from write queue
                    workflow.logger.info("Waiting for message from write queue...")
                    session_message = await write_queue.get()
                    if session_message is None:  # Shutdown signal
                        workflow.logger.info("Received shutdown signal")
                        break

                    workflow.logger.info(f"Routing message: {session_message}")
                    # Route to Nexus and get response
                    response = await self._route_to_nexus(session_message)
                    if response:
                        workflow.logger.info(f"Got response: {response}")
                        await read_queue.put(response)
            except asyncio.CancelledError:
                workflow.logger.info("Message router cancelled")
            except Exception as e:
                workflow.logger.error(f"Message router error: {e}", exc_info=True)
            finally:
                # Signal end of stream
                await read_queue.put(None)

        # Start router task
        router_task = asyncio.create_task(message_router())
        workflow.logger.info("Started message router task")

        try:
            yield read_stream, write_stream
        finally:
            workflow.logger.info("Cleaning up NexusTransport...")
            # Cleanup
            await write_stream.aclose()
            router_task.cancel()
            try:
                await router_task
            except asyncio.CancelledError:
                pass
            await read_stream.aclose()

    async def _route_to_nexus(
        self, session_message: SessionMessage
    ) -> Optional[SessionMessage]:
        """Route MCP message to appropriate Nexus operation."""
        message = session_message.message

        if not isinstance(message.root, types.JSONRPCRequest):
            return None

        request = message.root

        # Handle different MCP methods
        if request.method == "initialize":
            # For initialize, we return a mock response
            # In a full implementation, this could be a Nexus operation too
            result = types.InitializeResult(
                protocolVersion="2024-11-05",
                capabilities=types.ServerCapabilities(tools=types.ToolsCapability()),
                serverInfo=types.Implementation(
                    name="nexus-mcp-server", version="0.1.0"
                ),
            )

        elif request.method == "tools/list":
            from .mcp_server.nexus_service import ListToolsInput, MCPServerNexusService

            result = await self.nexus_client.execute_operation(
                MCPServerNexusService.list_tools,
                ListToolsInput(
                    operation_token=self.operation_token,
                    request=types.ListToolsRequest(method="tools/list"),
                ),
            )

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
        if isinstance(result, types.ErrorData):
            response_dict = {
                "jsonrpc": "2.0",
                "id": request.id,
                "error": result.model_dump(),
            }
        else:
            response_dict = {
                "jsonrpc": "2.0",
                "id": request.id,
                "result": result.model_dump()
                if hasattr(result, "model_dump")
                else result,
            }

        # Create response from dict
        response = types.JSONRPCResponse.model_validate(response_dict)

        return SessionMessage(types.JSONRPCMessage(root=response))


class AsyncioQueueStream:
    """Adapter to make asyncio.Queue compatible with anyio streams for MCP."""

    def __init__(self, queue: asyncio.Queue):
        self.queue = queue
        self._closed = False

    async def send(self, item: SessionMessage) -> None:
        if self._closed:
            raise anyio.ClosedResourceError()
        await self.queue.put(item)

    async def receive(self) -> SessionMessage:
        if self._closed:
            raise anyio.ClosedResourceError()
        item = await self.queue.get()
        if item is None:
            self._closed = True
            raise anyio.EndOfStream()
        return item

    def __aiter__(self):
        return self

    async def __anext__(self) -> SessionMessage:
        try:
            return await self.receive()
        except anyio.EndOfStream:
            raise StopAsyncIteration

    async def aclose(self) -> None:
        self._closed = True
        try:
            self.queue.put_nowait(None)
        except asyncio.QueueFull:
            pass


import anyio

# Make these available at module level
ClosedResourceError = anyio.ClosedResourceError
EndOfStream = anyio.EndOfStream


@asynccontextmanager
async def create_nexus_mcp_session(nexus_client, operation_token: str):
    """
    Create a standard MCP ClientSession using Nexus transport.
    This uses the real MCP SDK ClientSession with our custom transport.
    """
    from temporalio import workflow

    workflow.logger.info("Creating NexusTransport...")
    transport = NexusTransport(nexus_client, operation_token)

    workflow.logger.info("Connecting transport...")
    async with transport.connect() as (read_stream, write_stream):
        workflow.logger.info("Creating ClientSession...")
        async with ClientSession(read_stream, write_stream) as session:
            workflow.logger.info("Initializing MCP session...")
            await session.initialize()
            workflow.logger.info("MCP session initialized successfully")
            yield session
