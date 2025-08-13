import asyncio
import logging

from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile
from temporalio.worker import Worker

from updatable_timer import TASK_QUEUE
from updatable_timer.workflow import Workflow

interrupt_event = asyncio.Event()


async def main():
    logging.basicConfig(level=logging.INFO)

    config_dict = ClientConfigProfile.load().to_dict()
    config_dict.setdefault("address", "localhost:7233")
    config = ClientConfigProfile.from_dict(config_dict)
    client = await Client.connect(**config.to_client_connect_config())

    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[Workflow],
    ):
        logging.info("Worker started, ctrl+c to exit")
        # Wait until interrupted
        await interrupt_event.wait()
        logging.info("Interrupt received, shutting down...")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
