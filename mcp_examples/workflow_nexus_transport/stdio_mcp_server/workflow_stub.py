"""
A Temporal workflow that implements MCP server operations.
Returns mock data for testing purposes.
"""

import asyncio

from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    TextContent,
    Tool,
)
from temporalio import workflow


@workflow.defn
class MCPServerWorkflowStub:
    """A workflow that acts as an MCP server, handling tool listing and execution."""

    def __init__(self):
        pass

    @workflow.run
    async def run(self) -> None:
        print("🟢 workflow.run()")
        await asyncio.Future()

    @workflow.update
    async def list_tools(self, request: ListToolsRequest) -> ListToolsResult:
        """Handle list_tools requests."""
        print("🟢 list_tools()")
        return ListToolsResult(
            tools=[
                Tool(
                    name="sequentialthinking",
                    description="A tool for sequential thinking and problem-solving",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "thought": {"type": "string"},
                            "thoughtNumber": {"type": "integer"},
                            "totalThoughts": {"type": "integer"},
                            "nextThoughtNeeded": {"type": "boolean"},
                        },
                        "required": [
                            "thought",
                            "thoughtNumber",
                            "totalThoughts",
                            "nextThoughtNeeded",
                        ],
                    },
                )
            ]
        )

    @workflow.update
    async def call_tool(self, request: CallToolRequest) -> CallToolResult:
        """Handle call_tool requests."""
        print("🟢 call_tool()")
        if request.params.name == "sequentialthinking":
            args = request.params.arguments or {}
            thought = (
                args.get("thought", "Mock thought")
                if isinstance(args, dict)
                else "Mock thought"
            )
            thought_number = (
                args.get("thoughtNumber", 1) if isinstance(args, dict) else 1
            )
            total_thoughts = (
                args.get("totalThoughts", 3) if isinstance(args, dict) else 3
            )

            response_text = f"Mock response: Processed thought {thought_number}/{total_thoughts}: {thought}"

            return CallToolResult(
                content=[TextContent(type="text", text=response_text)]
            )
        else:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Mock response: Tool {request.params.name} called",
                    )
                ]
            )
