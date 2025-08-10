"""
Minimal MCP client using Nexus as the transport, and using a workflow-backed Nexus operation to
provide durable client sessions.

Avoids anyio dependencies of mcp.client.session.ClientSession that are incompatible with Temporal's
event loop.
"""

from typing import Any, Dict, Optional

import mcp.types as types
from temporalio.workflow import NexusClient

from mcp_sequential_thinking.mcp_server.nexus_service import (
    CallToolInput,
    ListToolsInput,
    MCPServerNexusService,
    MCPServerStartInput,
)


class NexusMCPClientSession:
    """A minimal MCP client that routes through Nexus."""

    def __init__(self, nexus_client: NexusClient[MCPServerNexusService]):
        self.nexus_client = nexus_client
        self.session_token: Optional[str] = None

    async def initialize(self) -> types.InitializeResult:
        """Initialize the MCP session by starting the workflow."""
        # Start the MCP server session workflow
        op_handle = await self.nexus_client.start_operation(
            MCPServerNexusService.start,
            MCPServerStartInput(
                mcp_server_workflow_name="SequentialThinkingMCPServerWorkflow"
            ),
        )
        self.session_token = op_handle.operation_token
        return types.InitializeResult(
            protocolVersion="2024-11-05",
            capabilities=types.ServerCapabilities(tools=types.ToolsCapability()),
            serverInfo=types.Implementation(name="nexus-mcp-server", version="0.1.0"),
        )

    async def list_tools(self) -> types.ListToolsResult:
        """List available tools."""
        if not self.session_token:
            raise RuntimeError("Client not initialized")
        return await self.nexus_client.execute_operation(
            MCPServerNexusService.list_tools,
            ListToolsInput(
                operation_token=self.session_token,
                request=types.ListToolsRequest(method="tools/list"),
            ),
        )

    async def call_tool(
        self, name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> types.CallToolResult:
        """Call a tool."""
        if not self.session_token:
            raise RuntimeError("Client not initialized")
        return await self.nexus_client.execute_operation(
            MCPServerNexusService.call_tool,
            CallToolInput(
                operation_token=self.session_token,
                request=types.CallToolRequest(
                    method="tools/call",
                    params=types.CallToolRequestParams(
                        name=name, arguments=arguments or {}
                    ),
                ),
            ),
        )

    async def close(self):
        """Close the client session."""
        self.session_token = None
