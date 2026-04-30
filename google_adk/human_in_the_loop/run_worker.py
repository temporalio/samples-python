from __future__ import annotations

import asyncio
from datetime import timedelta

from temporalio.client import Client
from temporalio.contrib.google_adk_agents import GoogleAdkPlugin, ModelActivityParameters
from temporalio.worker import Worker

from google_adk.human_in_the_loop.activities.sensitive_actions import (
    delete_record,
    send_email,
)
from google_adk.human_in_the_loop.workflows.hitl_workflow import (
    HumanInTheLoopWorkflow,
)


async def main():
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            GoogleAdkPlugin(
                model_params=ModelActivityParameters(
                    start_to_close_timeout=timedelta(seconds=30)
                )
            ),
        ],
    )

    worker = Worker(
        client,
        task_queue="google-adk-hitl-task-queue",
        workflows=[HumanInTheLoopWorkflow],
        activities=[send_email, delete_record],
    )
    print("Worker started on task queue: google-adk-hitl-task-queue")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
