import asyncio
import os

from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile

from sentry.worker import GreetingWorkflow


async def main():
    config = ClientConfigProfile.load()
    config["address"] = "localhost:7233"
    # Connect client
    client = await Client.connect(**config.to_client_connect_config())

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
