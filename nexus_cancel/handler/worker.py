"""
Worker for the handler namespace that processes Nexus operations and workflows.
"""

import asyncio
import logging
from typing import Optional

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from nexus_cancel.handler.service_handler import NexusServiceHandler
from nexus_cancel.handler.workflows import HelloHandlerWorkflow

interrupt_event = asyncio.Event()

NAMESPACE = "nexus-cancel-handler-namespace"
TASK_QUEUE = "nexus-cancel-handler-task-queue"


async def main(client: Optional[Client] = None):
    logging.basicConfig(level=logging.INFO)

    if not client:
        config = ClientConfig.load_client_connect_config()
        config.setdefault("target_host", "localhost:7233")
        config.setdefault("namespace", NAMESPACE)
        client = await Client.connect(**config)

    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[HelloHandlerWorkflow],
        nexus_service_handlers=[NexusServiceHandler()],
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
