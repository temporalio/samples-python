"""Worker for the MCP sample.

Registers an ``echo`` MCP server (the ``echo_mcp_server.py`` stdio script) with
the plugin. The plugin opens a pooled MCP connection on the worker and runs
``list_tools`` / ``call_tool`` as activities.
"""

import asyncio
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from google import genai
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from temporalio.client import Client
from temporalio.contrib.google_genai import GoogleGenAIPlugin
from temporalio.worker import Worker

from google_genai_plugin.mcp.workflow import McpWorkflow

ECHO_SERVER = str(Path(__file__).parent / "echo_mcp_server.py")


@asynccontextmanager
async def echo_session() -> AsyncIterator[ClientSession]:
    """Yield a connected, initialized session to the stdio echo MCP server."""
    params = StdioServerParameters(command=sys.executable, args=[ECHO_SERVER])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def main() -> None:
    genai_client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    plugin = GoogleGenAIPlugin(genai_client, mcp_servers={"echo": echo_session})

    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[plugin],
    )

    worker = Worker(
        client,
        task_queue="google-genai-mcp",
        workflows=[McpWorkflow],
    )
    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
