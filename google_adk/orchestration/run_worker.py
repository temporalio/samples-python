from __future__ import annotations

import asyncio

from temporalio.client import Client
from temporalio.contrib.google_adk_agents import GoogleAdkPlugin
from temporalio.worker import Worker

from google_adk.orchestration.workflows.loop_workflow import LoopWorkflow
from google_adk.orchestration.workflows.parallel_workflow import ParallelWorkflow
from google_adk.orchestration.workflows.sequential_workflow import SequentialWorkflow


async def main():
    client = await Client.connect(
        "localhost:7233",
        plugins=[GoogleAdkPlugin()],
    )

    worker = Worker(
        client,
        task_queue="google-adk-orchestration-task-queue",
        workflows=[SequentialWorkflow, ParallelWorkflow, LoopWorkflow],
    )
    print("Worker started on task queue: google-adk-orchestration-task-queue")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
