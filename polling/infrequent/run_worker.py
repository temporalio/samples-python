import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from polling.infrequent.activities import compose_greeting
from polling.infrequent.workflows import GreetingWorkflow
from util import get_temporal_config_path


async def main():
    config = ClientConfig.load_client_connect_config(
        config_file=str(get_temporal_config_path())
    )

    client = await Client.connect(**config)

    worker = Worker(
        client,
        task_queue="infrequent-activity-retry-task-queue",
        workflows=[GreetingWorkflow],
        activities=[compose_greeting],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
