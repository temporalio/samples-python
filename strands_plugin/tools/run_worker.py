"""Worker for the tools sample."""

# @@@SNIPSTART python-strands-tools-worker
import asyncio
import os

from temporalio.client import Client
from temporalio.contrib.strands import StrandsPlugin
from temporalio.worker import Worker

from strands_plugin.tools.workflow import (
    ToolsWorkflow,
    environment_activity,
    fetch_weather,
)


async def main() -> None:
    plugin = StrandsPlugin()
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[plugin],
    )

    worker = Worker(
        client,
        task_queue="strands-tools",
        workflows=[ToolsWorkflow],
        activities=[fetch_weather, environment_activity],
    )
    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
# @@@SNIPEND
