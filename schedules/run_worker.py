import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker
from your_activities import your_activity
from your_workflows import YourSchedulesWorkflow

from util import get_temporal_config_path


async def main():
    config = ClientConfig.load_client_connect_config(
        config_file=str(get_temporal_config_path())
    )

    client = await Client.connect(**config)
    worker = Worker(
        client,
        task_queue="schedules-task-queue",
        workflows=[YourSchedulesWorkflow],
        activities=[your_activity],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
