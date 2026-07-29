"""Tiny FastMCP server: exposes a single ``echo`` tool over stdio.

The worker launches this script as a subprocess and connects to it via the
MCP stdio transport. Swap it for any real MCP server in production.
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("echo-server")


@mcp.tool()
def echo(message: str) -> str:
    """Return the input message unchanged."""
    return message


if __name__ == "__main__":
    mcp.run()
