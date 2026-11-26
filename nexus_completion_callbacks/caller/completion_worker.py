"""Worker in the caller namespace that receives completion callbacks."""

import asyncio
import logging

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from nexus_completion_callbacks.caller.completion_handler import (
    GreetingCompletionHandler,
)
from nexus_completion_callbacks.caller.workflows import RecordCompletionWorkflow

COMPLETION_TASK_QUEUE = "nexus-completion-handler-task-queue"

interrupt_event = asyncio.Event()


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    config = ClientConfig.load_client_connect_config()
    _ = config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    async with Worker(
        client,
        task_queue=COMPLETION_TASK_QUEUE,
        nexus_service_handlers=[GreetingCompletionHandler()],
        workflows=[RecordCompletionWorkflow],
    ):
        logging.info("Completion Worker started, ctrl+c to exit")
        _ = await interrupt_event.wait()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
