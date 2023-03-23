import asyncio

from temporalio.client import Client
from temporalio.worker import Worker
from your_activities import your_activity
from your_workflows import YourSchedulesWorkflow


async def main():
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client,
        task_queue="schedules-task-queue",
        workflows=[YourSchedulesWorkflow],
        activities=[your_activity],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
