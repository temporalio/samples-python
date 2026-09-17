"""MCP server shared by the in-process, stdio, and HTTP samples."""

import argparse
from typing import Any

from mcp.server.mcpserver import MCPServer


def create_server() -> MCPServer[Any]:
    """Create the sample server with tools, prompts, and resources."""
    server = MCPServer("temporal-mcp-sample")

    @server.tool()
    def echo(value: str) -> str:
        """Return the supplied value unchanged."""
        return value

    @server.prompt()
    def greeting(name: str) -> str:
        """Create a greeting prompt."""
        return f"Hello, {name}!"

    @server.resource("sample://about", name="about")
    def about() -> str:
        """Describe this sample."""
        return "Temporal workflows can call MCP operations durably."

    @server.resource("sample://items/{item}", name="item")
    def item(item: str) -> str:
        """Return a resource identified by its path parameter."""
        return item

    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the sample MCP server")
    parser.add_argument(
        "transport",
        choices=("stdio", "streamable-http"),
        nargs="?",
        default="stdio",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    args = parser.parse_args()

    server = create_server()
    if args.transport == "stdio":
        server.run()
    else:
        server.run(
            transport="streamable-http",
            host=args.host,
            port=args.port,
            stateless_http=True,
        )


if __name__ == "__main__":
    main()
