import random

import requests
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("Tools Server")


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    print(f"[debug-server] add({a}, {b})")
    return a + b


@mcp.tool()
def get_secret_word() -> str:
    print("[debug-server] get_secret_word()")
    return random.choice(["apple", "banana", "cherry"])


@mcp.tool()
def get_current_weather(city: str) -> str:
    print(f"[debug-server] get_current_weather({city})")
    response = requests.get(f"https://wttr.in/{city}")
    return response.text


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
