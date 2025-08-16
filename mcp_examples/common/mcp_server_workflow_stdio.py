"""
A Temporal workflow that implements MCP server operations.
Returns mock data for testing purposes.
"""

from datetime import timedelta

from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
)
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from mcp_examples.common.mcp_server_workflow_stdio_activity import connect


@workflow.defn
class MCPServerWorkflow:
    """A workflow that acts as an MCP server, handling tool listing and execution."""

    def __init__(self):
        pass

    @workflow.run
    async def run(self) -> None:
        print("🟢 workflow.run()")
        await workflow.execute_activity(
            connect,
            start_to_close_timeout=timedelta(seconds=10),
        )

    @workflow.update
    async def list_tools(self, request: ListToolsRequest) -> ListToolsResult:
        """Handle list_tools requests."""
        print("🟢 list_tools()")
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
        print("🟢 call_tool()")
        return await workflow.execute_activity(
            "call-tool",
            args=[request],
            result_type=CallToolResult,
            task_queue="activity-specific-task-queue",
            schedule_to_close_timeout=timedelta(seconds=10),
        )
