"""Worker for the subagents sample."""

import asyncio
import os

from temporalio.client import Client
from temporalio.contrib.deepagents import DeepAgentsPlugin
from temporalio.worker import Worker

from deepagents_plugin.subagents.workflow import SubagentsWorkflow


async def main() -> None:
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[DeepAgentsPlugin()],
    )

    worker = Worker(
        client,
        task_queue="deepagents-subagents",
        workflows=[SubagentsWorkflow],
    )
    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
