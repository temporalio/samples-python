import argparse
import random

import requests
from mcp.server.fastmcp import FastMCP

# Create server
mcp = FastMCP("Tools Server")


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    print(f"[debug-server] add({a}, {b})")
    return a + b


@mcp.tool()
def get_secret_word() -> str:
    print("[debug-server] get_secret_word()")
    return random.choice(["apple", "banana", "cherry"])


@mcp.tool()
def get_current_weather(city: str) -> str:
    print(f"[debug-server] get_current_weather({city})")

    endpoint = "https://wttr.in"
    response = requests.get(f"{endpoint}/{city}")
    return response.text


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MCP Tools Server")
    parser.add_argument(
        "--transport",
        choices=["streamable-http", "sse"],
        default="streamable-http",
        help="Transport type (default: streamable-http)",
    )
    args = parser.parse_args()

    print(f"Starting Tools Server with {args.transport} transport...")
    mcp.run(transport=args.transport)
