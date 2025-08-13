import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile
from temporalio.worker import Worker
from your_activities import your_activity
from your_workflows import YourSchedulesWorkflow


async def main():
    config = ClientConfigProfile.load()
    config["address"] = "localhost:7233"
    client = await Client.connect(**config.to_client_connect_config())

    worker = Worker(
        client,
        task_queue="schedules-task-queue",
        workflows=[YourSchedulesWorkflow],
        activities=[your_activity],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
