"""Worker for the hello world sample (Graph API)."""

import asyncio
import os

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.worker import Worker

from langgraph_plugin.graph_api.hello_world.workflow import (
    HelloWorldWorkflow,
    build_graph,
)


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))
    plugin = LangGraphPlugin(graphs={"hello-world": build_graph()})

    worker = Worker(
        client,
        task_queue="langgraph-hello-world",
        workflows=[HelloWorldWorkflow],
        plugins=[plugin],
    )
    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
