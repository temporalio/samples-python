"""Worker for the hook-based HITL sample."""

import asyncio
import os

from temporalio.client import Client
from temporalio.contrib.strands import StrandsPlugin
from temporalio.worker import Worker

from strands_plugin.human_in_the_loop.workflow import HumanInTheLoopWorkflow


async def main() -> None:
    plugin = StrandsPlugin()
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[plugin],
    )

    worker = Worker(
        client,
        task_queue="strands-human-in-the-loop",
        workflows=[HumanInTheLoopWorkflow],
    )
    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
