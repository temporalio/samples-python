from datetime import timedelta

from mcp import StdioServerParameters
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
)
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from mcp_examples.nexus_transport.stdio_mcp_server.activity import (
        run_stdio_mcp_server,
    )


@workflow.defn
class MCPStdioClientSessionWorkflow:
    """A workflow that acts as an MCP client session, handling tool listing and execution."""

    def __init__(self):
        pass

    @workflow.run
    async def run(self, server_params: StdioServerParameters) -> None:
        await workflow.execute_activity(
            run_stdio_mcp_server,
            server_params,
            start_to_close_timeout=timedelta(days=999),
        )

    @workflow.update
    async def list_tools(self, request: ListToolsRequest) -> ListToolsResult:
        """Handle list_tools requests."""
        return await workflow.execute_activity(
            "list-tools",
            args=[request],
            result_type=ListToolsResult,
            task_queue="activity-specific-task-queue",
            schedule_to_close_timeout=timedelta(seconds=10),
        )

    @workflow.update
    async def call_tool(self, request: CallToolRequest) -> CallToolResult:
        """Handle call_tool requests."""
        return await workflow.execute_activity(
            "call-tool",
            args=[request],
            result_type=CallToolResult,
            task_queue="activity-specific-task-queue",
            schedule_to_close_timeout=timedelta(seconds=10),
        )
