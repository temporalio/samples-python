import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from message_passing.message_handler_waiting_compensation_cleanup import TASK_QUEUE
from message_passing.message_handler_waiting_compensation_cleanup.activities import (
    my_activity,
)
from message_passing.message_handler_waiting_compensation_cleanup.workflows import (
    MyWorkflow,
)

interrupt_event = asyncio.Event()


async def main():
    logging.basicConfig(level=logging.INFO)

    client = await Client.connect("localhost:7233")

    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[MyWorkflow],
        activities=[my_activity],
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
