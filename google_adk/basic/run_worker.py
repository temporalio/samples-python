from __future__ import annotations

import asyncio

from temporalio.client import Client
from temporalio.contrib.google_adk_agents import GoogleAdkPlugin
from temporalio.worker import Worker

from google_adk.basic.activities.get_weather_activity import get_weather
from google_adk.basic.activities.search_web_activity import search_web
from google_adk.basic.workflows.hello_world_workflow import HelloWorldWorkflow
from google_adk.basic.workflows.tools_workflow import ToolsWorkflow


async def main():
    client = await Client.connect(
        "localhost:7233",
        plugins=[GoogleAdkPlugin()],
    )

    worker = Worker(
        client,
        task_queue="google-adk-basic-task-queue",
        workflows=[HelloWorldWorkflow, ToolsWorkflow],
        activities=[get_weather, search_web],
    )
    print("Worker started on task queue: google-adk-basic-task-queue")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
