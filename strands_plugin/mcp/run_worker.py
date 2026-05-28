"""Worker for the MCP sample.

The worker launches the ``echo_mcp_server.py`` script as a subprocess at
startup. The plugin opens a stdio MCP session, enumerates tools once, and
caches the schema for the worker's lifetime.
"""

import asyncio
import os
import sys
from pathlib import Path

from mcp import StdioServerParameters, stdio_client
from strands.tools.mcp.mcp_client import MCPClient
from temporalio.client import Client
from temporalio.contrib.strands import StrandsPlugin
from temporalio.worker import Worker

from strands_plugin.mcp.workflow import MCPWorkflow

ECHO_SERVER = Path(__file__).parent / "echo_mcp_server.py"


def _make_echo_client() -> MCPClient:
    return MCPClient(
        lambda: stdio_client(
            StdioServerParameters(
                command=sys.executable,
                args=[str(ECHO_SERVER)],
            )
        )
    )


async def main() -> None:
    plugin = StrandsPlugin(mcp_clients={"echo": _make_echo_client})
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[plugin],
    )

    worker = Worker(
        client,
        task_queue="strands-mcp",
        workflows=[MCPWorkflow],
    )
    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
