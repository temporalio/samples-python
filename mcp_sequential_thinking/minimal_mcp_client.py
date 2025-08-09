"""
Minimal MCP client that works within Temporal workflow constraints.
Avoids anyio dependencies that are incompatible with Temporal's event loop.
"""

import json
from typing import Any, Dict, Optional

import mcp.types as types
from temporalio.workflow import NexusClient

from mcp_sequential_thinking.mcp_server.nexus_service import (
    CallToolInput,
    ListToolsInput,
    MCPServerNexusService,
    MCPServerStartInput,
)


class MinimalMCPClient:
    """A minimal MCP client that routes through Nexus without anyio dependencies."""

    def __init__(self, nexus_client: NexusClient[MCPServerNexusService]):
        self.nexus_client = nexus_client
        self.operation_token: Optional[str] = None
        self._initialized = False

    async def initialize(self) -> types.InitializeResult:
        """Initialize the MCP session by starting the workflow."""
        # Start the MCP server workflow - this creates our session
        op_handle = await self.nexus_client.start_operation(
            MCPServerNexusService.start,
            MCPServerStartInput(
                mcp_server_workflow_name="SequentialThinkingMCPServerWorkflow"
            ),
        )

        # Store the operation token for subsequent calls
        self.operation_token = op_handle.operation_token
        self._initialized = True

        # Return the initialization result
        return types.InitializeResult(
            protocolVersion="2024-11-05",  # Use a supported version
            capabilities=types.ServerCapabilities(tools=types.ToolsCapability()),
            serverInfo=types.Implementation(name="nexus-mcp-server", version="0.1.0"),
        )

    async def list_tools(self) -> types.ListToolsResult:
        """List available tools."""
        if not self._initialized or not self.operation_token:
            raise RuntimeError("Client not initialized")

        result = await self.nexus_client.execute_operation(
            MCPServerNexusService.list_tools,
            ListToolsInput(
                operation_token=self.operation_token,
                request=types.ListToolsRequest(method="tools/list"),
            ),
        )
        return result

    async def call_tool(
        self, name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Call a tool."""
        if not self._initialized or not self.operation_token:
            raise RuntimeError("Client not initialized")

        result = await self.nexus_client.execute_operation(
            MCPServerNexusService.call_tool,
            CallToolInput(
                operation_token=self.operation_token,
                request=types.CallToolRequest(
                    method="tools/call",
                    params=types.CallToolRequestParams(
                        name=name, arguments=arguments or {}
                    ),
                ),
            ),
        )

        # Extract the actual content from the result
        if hasattr(result, "content") and result.content:
            # Parse the JSON content from the tool result
            content = result.content[0]
            if hasattr(content, "text"):
                try:
                    return json.loads(content.text)
                except json.JSONDecodeError:
                    return content.text
        return result

    async def close(self):
        """Close the client (no-op for Nexus transport)."""
        self._initialized = False
