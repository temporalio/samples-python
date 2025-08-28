import asyncio
import logging
from pathlib import Path

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from message_passing.introduction import TASK_QUEUE
from message_passing.introduction.activities import call_greeting_service
from message_passing.introduction.workflows import GreetingWorkflow

interrupt_event = asyncio.Event()


async def main():
    logging.basicConfig(level=logging.INFO)

    # Get repo root - 2 levels deep from root

    repo_root = Path(__file__).resolve().parent.parent.parent

    config_file = repo_root / "temporal.toml"
    config = ClientConfig.load_client_connect_config(config_file=str(config_file))
    config["target_host"] = "localhost:7233"
    client = await Client.connect(**config)

    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[GreetingWorkflow],
        activities=[call_greeting_service],
    ):
        logging.info("Worker started, ctrl+c to exit")
        await interrupt_event.wait()
        logging.info("Shutting down")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
