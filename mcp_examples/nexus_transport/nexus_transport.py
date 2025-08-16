import asyncio
from contextlib import asynccontextmanager
from typing import Optional

import anyio
import mcp.types as types
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from mcp.shared.message import SessionMessage
from temporalio import workflow

from mcp_examples.nexus_transport.mcp_server_nexus_service import (
    CallToolInput,
    ListToolsInput,
    MCPServerInput,
    MCPServerNexusService,
)


class NexusTransport:
    def __init__(
        self,
        nexus_client: workflow.NexusClient[MCPServerNexusService],
        mcp_server_input: MCPServerInput,
    ):
        self.nexus_client = nexus_client
        self.mcp_server_input = mcp_server_input
        self.operation_token: Optional[str] = None

    @asynccontextmanager
    async def connect(self):
        read_queue = asyncio.Queue()
        write_queue = asyncio.Queue()

        read_stream = AsyncioQueueStream(read_queue)
        write_stream = AsyncioQueueStream(write_queue)

        async def message_router():
            try:
                while True:
                    session_message = await write_queue.get()
                    if session_message is None:
                        break

                    response = await self._route_to_nexus(session_message)
                    if response:
                        await read_queue.put(response)
            except asyncio.CancelledError:
                pass
            finally:
                await read_queue.put(None)

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
            await read_stream.aclose()

    async def _route_to_nexus(
        self, session_message: SessionMessage
    ) -> Optional[SessionMessage]:
        message = session_message.message

        if not isinstance(message.root, types.JSONRPCRequest):
            return None

        request = message.root

        if request.method == "initialize":
            workflow_handle = await self.nexus_client.start_operation(
                MCPServerNexusService.start,
                self.mcp_server_input,
            )
            assert workflow_handle.operation_token
            self.operation_token = workflow_handle.operation_token

            result = types.InitializeResult(
                protocolVersion="2024-11-05",
                capabilities=types.ServerCapabilities(tools=types.ToolsCapability()),
                serverInfo=types.Implementation(
                    name="nexus-mcp-server", version="0.1.0"
                ),
            )

        elif request.method == "tools/list":
            if not self.operation_token:
                result = types.ErrorData(
                    code=types.INTERNAL_ERROR, message="Not initialized"
                )
            else:
                result = await self.nexus_client.execute_operation(
                    MCPServerNexusService.list_tools,
                    ListToolsInput(
                        operation_token=self.operation_token,
                        request=types.ListToolsRequest(method="tools/list"),
                    ),
                )

        elif request.method == "tools/call":
            if not self.operation_token:
                result = types.ErrorData(
                    code=types.INTERNAL_ERROR, message="Not initialized"
                )
            else:
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

        response = types.JSONRPCResponse.model_validate(response_dict)

        return SessionMessage(types.JSONRPCMessage(root=response))


class AsyncioQueueStream(
    MemoryObjectSendStream[SessionMessage], MemoryObjectReceiveStream[SessionMessage]
):
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

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()
        return None
