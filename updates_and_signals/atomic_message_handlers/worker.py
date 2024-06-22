import asyncio
import logging
from temporalio import activity, common, workflow
from temporalio.client import Client, WorkflowHandle
from temporalio.worker import Worker

from updates_and_signals.atomic_message_handlers.workflow import ClusterManagerWorkflow, allocate_nodes_to_job, deallocate_nodes_for_job, find_bad_nodes

interrupt_event = asyncio.Event()

async def main():
    # Connect client
    client = await Client.connect("localhost:7233")

    async with Worker(
        client,
        task_queue="atomic-message-handlers-task-queue",
        workflows=[ClusterManagerWorkflow],
        activities=[allocate_nodes_to_job, deallocate_nodes_for_job, find_bad_nodes],
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
