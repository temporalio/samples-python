"""Worker for the hello world sample.

``DeepAgentsPlugin`` is a client-level plugin: add it to ``Client.connect(...)``
and the SDK propagates it to every Worker built from that client. The plugin
registers the ``deepagents.*`` activities and installs the LangChain-aware data
converter, so the worker needs no other wiring.
"""

# @@@SNIPSTART python-deepagents-hello-world-worker
import asyncio
import os

from temporalio.client import Client
from temporalio.contrib.deepagents import DeepAgentsPlugin
from temporalio.worker import Worker

from deepagents_plugin.hello_world.workflow import HelloWorldAgent


async def main() -> None:
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[DeepAgentsPlugin()],
    )

    worker = Worker(
        client,
        task_queue="deepagents-hello-world",
        workflows=[HelloWorldAgent],
    )
    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
# @@@SNIPEND
