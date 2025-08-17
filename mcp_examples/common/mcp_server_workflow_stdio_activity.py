from mcp import ClientSession, ListToolsResult, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolRequest, CallToolResult, ListToolsRequest
from temporalio import activity
from temporalio.worker import Worker


@activity.defn
async def connect():
    server_params = StdioServerParameters(
        command="npx", args=["-y", "@modelcontextprotocol/server-sequential-thinking"]
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            @activity.defn(name="list-tools")
            async def list_tools(request: ListToolsRequest) -> ListToolsResult:
                return await session.list_tools()

            @activity.defn(name="call-tool")
            async def call_tool(request: CallToolRequest) -> CallToolResult:
                return await session.call_tool(
                    request.params.name, request.params.arguments
                )

            worker = Worker(
                activity.client(),
                task_queue="activity-specific-task-queue",
                activities=[list_tools, call_tool],
            )
            await worker.run()
