import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from polling.infrequent.activities import ComposeGreeting
from polling.infrequent.workflows import GreetingWorkflow


async def main():
    client = await Client.connect("localhost:7233")
    activities = ComposeGreeting()
    worker = Worker(
        client,
        task_queue="infrequent-activity-retry-task-queue",
        workflows=[GreetingWorkflow],
        activities=[activities.compose_greeting],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
