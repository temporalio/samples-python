"""A minimal stdio MCP server used by the MCP sample."""

from mcp.server.mcpserver import MCPServer

mcp = MCPServer("echo-server")


@mcp.tool()
def echo(message: str) -> str:
    """Return the input message unchanged."""
    return message


if __name__ == "__main__":
    mcp.run()
