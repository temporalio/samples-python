import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from polling.periodic_sequence.activities import ComposeGreeting
from polling.periodic_sequence.workflows import ChildWorkflow, GreetingWorkflow


async def main():
    client = await Client.connect("localhost:7233")
    activities = ComposeGreeting()
    worker = Worker(
        client,
        task_queue="periodic-retry-task-queue",
        workflows=[GreetingWorkflow, ChildWorkflow],
        activities=[activities.compose_greeting],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
