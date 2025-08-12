import asyncio
import os

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from sentry.worker import GreetingWorkflow
from util import get_temporal_config_path


async def main():
    config = ClientConfig.load_client_connect_config(
        config_file=str(get_temporal_config_path())
    )

    # Connect client
    client = await Client.connect(**config)

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
