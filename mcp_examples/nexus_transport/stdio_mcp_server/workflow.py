from datetime import timedelta

from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
)
from temporalio import workflow

from mcp_examples.nexus_transport.mcp_server_nexus_service import (
    MCPServerInput,
    MCPServiceWorkflowBase,
)

with workflow.unsafe.imports_passed_through():
    from mcp_examples.nexus_transport.stdio_mcp_server.activity import (
        run_stdio_mcp_server,
    )


@workflow.defn
class MCPStdioClientSessionWorkflow(MCPServiceWorkflowBase):
    """A workflow that acts as an MCP client session, handling tool listing and execution."""

    @workflow.run
    async def run(self, input: MCPServerInput) -> None:
        assert input.stdio_server_params
        await workflow.execute_activity(
            run_stdio_mcp_server,
            input.stdio_server_params,
            start_to_close_timeout=timedelta(days=999),
        )

    @workflow.update
    async def list_tools(self, request: ListToolsRequest) -> ListToolsResult:
        return await workflow.execute_activity(
            "list-tools",
            args=[request],
            result_type=ListToolsResult,
            task_queue="activity-specific-task-queue",
            schedule_to_close_timeout=timedelta(seconds=10),
        )

    @workflow.update
    async def call_tool(self, request: CallToolRequest) -> CallToolResult:
        return await workflow.execute_activity(
            "call-tool",
            args=[request],
            result_type=CallToolResult,
            task_queue="activity-specific-task-queue",
            schedule_to_close_timeout=timedelta(seconds=10),
        )
