import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from polling.frequent.activities import compose_greeting
from polling.frequent.workflows import GreetingWorkflow


async def main():
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="frequent-activity-retry-task-queue",
        workflows=[GreetingWorkflow],
        activities=[compose_greeting],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
