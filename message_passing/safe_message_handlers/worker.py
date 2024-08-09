import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from message_passing.safe_message_handlers.workflow import (
    ClusterManagerWorkflow,
    assign_nodes_to_job,
    find_bad_nodes,
    unassign_nodes_for_job,
)

interrupt_event = asyncio.Event()


async def main():
    # Connect client
    client = await Client.connect("localhost:7233")

    async with Worker(
        client,
        task_queue="safe-message-handlers-task-queue",
        workflows=[ClusterManagerWorkflow],
        activities=[assign_nodes_to_job, unassign_nodes_for_job, find_bad_nodes],
    ):
        # Wait until interrupted
        logging.info("ClusterManagerWorkflow worker started, ctrl+c to exit")
        await interrupt_event.wait()
        logging.info("Shutting down")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
