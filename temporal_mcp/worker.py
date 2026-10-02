"""Run a Worker configured for one of the sample MCP transports."""

import argparse
import asyncio
import sys
from collections.abc import Callable
from pathlib import Path
from typing import cast

from mcp import Client as MCPClient
from mcp import StdioServerParameters, stdio_client
from temporalio.client import Client as TemporalClient
from temporalio.envconfig import ClientConfig
from temporalio.mcp import MCPPlugin
from temporalio.worker import Worker

from server import create_server
from workflow import TRANSPORTS, MCPDemoWorkflow, Transport, client_name, task_queue

SERVER_PATH = Path(__file__).parent / "server.py"
DEFAULT_HTTP_URL = "http://127.0.0.1:8000/mcp"


def client_factory(
    transport: Transport, http_url: str = DEFAULT_HTTP_URL
) -> Callable[[], MCPClient]:
    """Create the worker-side client factory for a transport."""
    if transport == "in-process":
        return lambda: MCPClient(create_server())
    if transport == "stdio":
        parameters = StdioServerParameters(
            command=sys.executable,
            args=[str(SERVER_PATH), "stdio"],
        )
        return lambda: MCPClient(stdio_client(parameters))
    return lambda: MCPClient(http_url)


def create_plugin(transport: Transport, http_url: str = DEFAULT_HTTP_URL) -> MCPPlugin:
    return MCPPlugin({client_name(transport): client_factory(transport, http_url)})


async def main(transport: Transport, http_url: str) -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await TemporalClient.connect(
        **config,
        plugins=[create_plugin(transport, http_url)],
    )

    worker = Worker(
        client,
        task_queue=task_queue(transport),
        workflows=[MCPDemoWorkflow],
    )
    print(f"Worker started for {transport}. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transport", choices=TRANSPORTS)
    parser.add_argument("--http-url", default=DEFAULT_HTTP_URL)
    args = parser.parse_args()
    asyncio.run(main(cast(Transport, args.transport), args.http_url))
