from mcp.server.fastmcp import FastMCP

server = FastMCP("support-directory")


@server.tool()
def support_hours() -> str:
    return "Support is staffed 09:00-17:00 UTC."


if __name__ == "__main__":
    server.run()
