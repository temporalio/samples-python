"""Worker that hosts the Nexus service for standalone operations sample."""

import asyncio
import logging

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from nexus_standalone_operations.handler import HelloWorkflow, MyNexusServiceHandler

interrupt_event = asyncio.Event()

TASK_QUEUE = "nexus-standalone-operations"


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    config = ClientConfig.load_client_connect_config()
    _ = config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[HelloWorkflow],
        nexus_service_handlers=[MyNexusServiceHandler()],
    ):
        logging.info("Worker started, ctrl+c to exit")
        _ = await interrupt_event.wait()
        logging.info("Shutting down")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
