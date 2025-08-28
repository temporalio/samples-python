import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from polling.frequent.workflows import GreetingWorkflow


async def main():
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    result = await client.execute_workflow(
        GreetingWorkflow.run,
        "World",
        id="frequent-activity-retry",
        task_queue="frequent-activity-retry-task-queue",
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
