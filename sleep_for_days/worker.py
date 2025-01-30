import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from sleep_for_days import TASK_QUEUE
from sleep_for_days.activities import send_email
from sleep_for_days.workflows import SleepForDaysWorkflow


async def main():
    client = await Client.connect("localhost:7233")

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
