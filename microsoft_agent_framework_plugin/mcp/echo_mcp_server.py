"""A one-tool MCP server over stdio. The Worker starts it as a subprocess."""

# @@@SNIPSTART python-microsoft-agent-framework-mcp-server
from mcp.server.mcpserver import MCPServer

server = MCPServer("echo")


@server.tool()
def echo(message: str) -> str:
    """Return the message unchanged."""
    return message


if __name__ == "__main__":
    server.run()
# @@@SNIPEND
