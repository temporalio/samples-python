import asyncio
import logging

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from message_passing.update_with_start.lazy_initialization import TASK_QUEUE, workflows
from message_passing.update_with_start.lazy_initialization.activities import get_price

interrupt_event = asyncio.Event()


async def main():
    logging.basicConfig(level=logging.INFO)

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[workflows.ShoppingCartWorkflow],
        activities=[get_price],
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
