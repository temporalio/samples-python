import sys
from pathlib import Path
from typing import Any

from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

ECHO_SERVER = Path(__file__).parent / "echo_mcp_server.py"


# @@@SNIPSTART google-adk-agents-mcp-echo-toolset-factory
def echo_toolset(_: Any | None) -> McpToolset:
    """Build an McpToolset over the local echo MCP server.

    The server is the in-repo echo_mcp_server.py script, launched as a
    subprocess with the current Python interpreter. This factory only runs
    inside an activity or a local ADK run, never inside workflow code.
    """
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=sys.executable,
                args=[str(ECHO_SERVER)],
            ),
        ),
    )


# @@@SNIPEND
