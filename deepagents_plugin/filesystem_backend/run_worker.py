"""Worker for the filesystem backend sample."""

import asyncio
import os

from temporalio.client import Client
from temporalio.contrib.deepagents import DeepAgentsPlugin
from temporalio.worker import Worker

from deepagents_plugin.filesystem_backend.workflow import FilesystemAgent


async def main() -> None:
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[DeepAgentsPlugin()],
    )

    worker = Worker(
        client,
        task_queue="deepagents-filesystem-backend",
        workflows=[FilesystemAgent],
    )
    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
