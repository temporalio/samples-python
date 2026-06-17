from __future__ import annotations

import asyncio

from temporalio.client import Client
from temporalio.contrib.google_adk_agents import GoogleAdkPlugin
from temporalio.worker import Worker

from google_adk_agents.streaming.workflows.streaming_workflow import (
    StreamingAgentWorkflow,
)


async def main():
    # Construct the plugin once and share the same instance between the
    # client and the worker.
    plugin = GoogleAdkPlugin()

    client = await Client.connect("localhost:7233", plugins=[plugin])

    worker = Worker(
        client,
        task_queue="google-adk-agents-streaming",
        workflows=[StreamingAgentWorkflow],
        plugins=[plugin],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
