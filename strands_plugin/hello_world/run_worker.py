"""Worker for the hello world sample."""

# @@@SNIPSTART python-strands-hello-world-worker
import asyncio
import os

from temporalio.client import Client
from temporalio.contrib.strands import StrandsPlugin
from temporalio.worker import Worker

from strands_plugin.hello_world.workflow import HelloWorldWorkflow


async def main() -> None:
    plugin = StrandsPlugin()
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[plugin],
    )

    worker = Worker(
        client,
        task_queue="strands-hello-world",
        workflows=[HelloWorldWorkflow],
    )
    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
# @@@SNIPEND
