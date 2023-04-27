import asyncio

from temporalio.client import Client
from workflows import GreetingWorkflow


async def main():
    client = await Client.connect("localhost:7233")
    result = await client.execute_workflow(
        GreetingWorkflow.run,
        "World",
        id="infrequent-activity-retry",
        task_queue="infrequent-activity-retry-task-queue",
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
