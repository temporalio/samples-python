import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from sleep_for_days import TASK_QUEUE
from sleep_for_days.activities import send_email
from sleep_for_days.workflows import SleepForDaysWorkflow


async def main():
        # Get repo root - 1 level deep from root
        repo_root = Path(__file__).resolve().parent.parent
        config_file = repo_root / "temporal.toml"
    config = ClientConfig.load_client_connect_config(config_file=str(config_file))
    config["target_host"] = "localhost:7233"
    client = await Client.connect(**config)

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
