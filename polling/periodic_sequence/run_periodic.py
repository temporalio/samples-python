import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from polling.periodic_sequence.workflows import GreetingWorkflow
from util import get_temporal_config_path


async def main():
    config = ClientConfig.load_client_connect_config(
        config_file=str(get_temporal_config_path())
    )

    client = await Client.connect(**config)
    result = await client.execute_workflow(
        GreetingWorkflow.run,
        "World",
        id="periodic-child-workflow-retry",
        task_queue="periodic-retry-task-queue",
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
