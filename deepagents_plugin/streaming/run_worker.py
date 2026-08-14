"""Worker for the streaming sample.

``streaming_topic=`` is what turns on streaming: with it set, the plugin routes
model calls through the ``deepagents.invoke_model_streaming`` activity, which
publishes chunk batches to that workflow-streams topic.
"""

import asyncio
import os

from temporalio.client import Client
from temporalio.contrib.deepagents import DeepAgentsPlugin
from temporalio.worker import Worker

from deepagents_plugin.streaming.workflow import STREAMING_TOPIC, StreamingWorkflow


async def main() -> None:
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[DeepAgentsPlugin(streaming_topic=STREAMING_TOPIC)],
    )

    worker = Worker(
        client,
        task_queue="deepagents-streaming",
        workflows=[StreamingWorkflow],
    )
    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
