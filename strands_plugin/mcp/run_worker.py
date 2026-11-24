"""Worker for the MCP sample.

The worker launches the ``echo_mcp_server.py`` script as a subprocess when an
MCP activity first needs it, and reuses that connection until it sits idle.
"""

# @@@SNIPSTART python-strands-mcp-worker
import asyncio
import os
import sys
from pathlib import Path

import mcp
from temporalio.client import Client
from temporalio.strands_agents import StrandsPlugin
from temporalio.worker import Worker

from strands_plugin.mcp.workflow import MCPWorkflow

ECHO_SERVER = Path(__file__).parent / "echo_mcp_server.py"


# Return a new mcp.Client on every call: the plugin calls the factory each time
# it opens a connection.
def _make_echo_client() -> mcp.Client:
    return mcp.Client(
        mcp.StdioServerParameters(
            command=sys.executable,
            args=[str(ECHO_SERVER)],
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
# @@@SNIPEND
