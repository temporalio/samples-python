from __future__ import annotations

import asyncio

from temporalio.client import Client
from temporalio.contrib.opentelemetry import TracingInterceptor
from temporalio.worker import Worker

from activities.basic_model_activity import basic_model_invocation
from workflows.basic_model_workflow import BasicModelWorkflow


async def main():
    # Create client connected to server at the given address
    client = await Client.connect(
        "localhost:7233",
    )

    worker = Worker(
        client,
        task_queue="openai-basic-task-queue",
        workflows=[
            BasicModelWorkflow,
        ],
        activities=[
            basic_model_invocation,
        ],
        interceptors=[TracingInterceptor()]
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
