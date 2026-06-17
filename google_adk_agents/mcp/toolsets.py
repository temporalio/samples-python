import os
from typing import Any

from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters


# @@@SNIPSTART google-adk-agents-mcp-toolset-factory
def filesystem_toolset(_: Any | None) -> McpToolset:
    """Build an McpToolset over the filesystem MCP server.

    The server is exposed read/write access to this sample's own directory. The
    directory path is read here (in the factory), which only runs inside an
    activity or a local ADK run -- never inside workflow code.
    """
    exposed_dir = os.path.dirname(os.path.abspath(__file__))
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="npx",
                args=[
                    "-y",
                    "@modelcontextprotocol/server-filesystem",
                    exposed_dir,
                ],
            ),
        ),
    )


# @@@SNIPEND
