#!/usr/bin/env python3

import asyncio

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin
from temporalio.worker import Worker

from openai_agents.reasoning_content.activities.reasoning_activities import (
    get_reasoning_response,
)
from openai_agents.reasoning_content.workflows.reasoning_content_workflow import (
    ReasoningContentWorkflow,
)


async def main():
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(),
        ],
    )

    worker = Worker(
        client,
        task_queue="reasoning-content-task-queue",
        workflows=[ReasoningContentWorkflow],
        activities=[get_reasoning_response],
    )

    print("Starting reasoning content worker...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
