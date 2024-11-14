import asyncio
import os

from temporalio.client import Client

from sentry_v1.worker import GreetingWorkflow


async def main():
    # Connect client
    client = await Client.connect("localhost:7233")

    # Run workflow
    result = await client.execute_workflow(
        GreetingWorkflow.run,
        "World",
        id="sentry-workflow-id",
        task_queue="sentry-task-queue",
    )
    print(f"Workflow result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
