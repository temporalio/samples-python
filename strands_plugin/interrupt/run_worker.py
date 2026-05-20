"""Worker for the tool-body interrupt sample."""

import asyncio
import os

from temporalio.client import Client
from temporalio.contrib.strands import StrandsPlugin
from temporalio.worker import Worker

from strands_plugin.interrupt.workflow import InterruptWorkflow, delete_thing


async def main() -> None:
    plugin = StrandsPlugin()
    # The plugin MUST be on the client so its failure converter is installed.
    # Without it, the activity's InterruptException cannot survive serialization
    # across the activity boundary as an Interrupt.
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[plugin],
    )

    worker = Worker(
        client,
        task_queue="strands-interrupt",
        workflows=[InterruptWorkflow],
        activities=[delete_thing],
    )
    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
