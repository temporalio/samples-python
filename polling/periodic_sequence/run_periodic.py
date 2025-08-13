import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile

from polling.periodic_sequence.workflows import GreetingWorkflow


async def main():
    config = ClientConfigProfile.load()
    config["address"] = "localhost:7233"
    client = await Client.connect(**config.to_client_connect_config())

    result = await client.execute_workflow(
        GreetingWorkflow.run,
        "World",
        id="periodic-child-workflow-retry",
        task_queue="periodic-retry-task-queue",
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
