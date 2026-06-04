"""Worker for the streaming sample (Graph API)."""

import asyncio
import os

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.worker import Worker

from langgraph_plugin.graph_api.streaming.workflow import (
    StreamingWorkflow,
    make_streaming_graph,
)


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))
    # streaming_topic routes node get_stream_writer() output onto the "tokens" topic.
    plugin = LangGraphPlugin(
        graphs={"streaming": make_streaming_graph()},
        streaming_topic="tokens",
    )

    worker = Worker(
        client,
        task_queue="langgraph-streaming",
        workflows=[StreamingWorkflow],
        plugins=[plugin],
    )
    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
