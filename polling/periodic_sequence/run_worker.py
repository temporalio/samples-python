import asyncio

from activities import compose_greeting
from temporalio.client import Client
from temporalio.worker import Worker
from workflows import ChildWorkflow, GreetingWorkflow


async def main():
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="periodic-retry-task-queue",
        workflows=[GreetingWorkflow, ChildWorkflow],
        activities=[compose_greeting],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
