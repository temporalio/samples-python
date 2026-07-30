"""Worker for the activity interrupt sample."""

# @@@SNIPSTART python-strands-activity-interrupt-worker
import asyncio
import os

from temporalio.client import Client
from temporalio.contrib.strands import StrandsPlugin
from temporalio.worker import Worker

from strands_plugin.activity_interrupt.workflow import (
    ActivityInterruptWorkflow,
    delete_thing,
)


async def main() -> None:
    plugin = StrandsPlugin()
    # The plugin MUST be on the client so its failure converter is installed.
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[plugin],
    )

    worker = Worker(
        client,
        task_queue="strands-activity-interrupt",
        workflows=[ActivityInterruptWorkflow],
        activities=[delete_thing],
    )
    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
# @@@SNIPEND
