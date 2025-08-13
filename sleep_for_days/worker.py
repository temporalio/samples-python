import asyncio
import logging

from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile
from temporalio.worker import Worker

from sleep_for_days import TASK_QUEUE
from sleep_for_days.activities import send_email
from sleep_for_days.workflows import SleepForDaysWorkflow


async def main():
    config_dict = ClientConfigProfile.load().to_dict()
    config_dict.setdefault("address", "localhost:7233")
    config = ClientConfigProfile.from_dict(config_dict)
    client = await Client.connect(**config.to_client_connect_config())

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[SleepForDaysWorkflow],
        activities=[send_email],
    )

    await worker.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
