"""
A Nexus service that presents the interface of an MCP server.
Returns mock data for testing the transport layer.
"""

from dataclasses import dataclass

import nexusrpc
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    TextContent,
    Tool,
)


@dataclass
class MCPServerStartInput:
    mcp_server_workflow_name: str


@dataclass
class ListToolsInput:
    operation_token: str
    request: ListToolsRequest


@dataclass
class CallToolInput:
    operation_token: str
    request: CallToolRequest


@nexusrpc.service
class MCPServerNexusService:
    start: nexusrpc.Operation[MCPServerStartInput, None]
    list_tools: nexusrpc.Operation[ListToolsInput, ListToolsResult]
    call_tool: nexusrpc.Operation[CallToolInput, CallToolResult]


@nexusrpc.handler.service_handler(service=MCPServerNexusService)
class MCPServerNexusServiceHandler:
    @nexusrpc.handler.sync_operation
    async def start(
        self, ctx: nexusrpc.handler.StartOperationContext, input: MCPServerStartInput
    ) -> None:
        # Mock implementation - just return None
        return None

    @nexusrpc.handler.sync_operation
    async def call_tool(
        self, ctx: nexusrpc.handler.StartOperationContext, input: CallToolInput
    ) -> CallToolResult:
        # Mock implementation - return a sample response
        if input.request.params.name == "sequentialthinking":
            args = input.request.params.arguments or {}
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
                        text=f"Mock response: Tool {input.request.params.name} called",
                    )
                ]
            )

    @nexusrpc.handler.sync_operation
    async def list_tools(
        self, ctx: nexusrpc.handler.StartOperationContext, input: ListToolsInput
    ) -> ListToolsResult:
        # Mock implementation - return sequential thinking tool
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
