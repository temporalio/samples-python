"""Worker for the hooks sample."""

import asyncio
import os

from temporalio.client import Client
from temporalio.contrib.strands import StrandsPlugin
from temporalio.worker import Worker

from strands_plugin.hooks.workflow import HooksWorkflow, persist_tool_call


async def main() -> None:
    plugin = StrandsPlugin()
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[plugin],
    )

    worker = Worker(
        client,
        task_queue="strands-hooks",
        workflows=[HooksWorkflow],
        activities=[persist_tool_call],
    )
    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
