import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker
from mutexworkflow import MutexWorkflow, signal_with_start_mutex_workflow
from workflow import SampleWorkflowWithMutex

# reference: https://github.com/temporalio/samples-go/blob/main/mutex/mutex_workflow.go


interrupt_event = asyncio.Event()


async def main():
    # set up logging facility
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    # Start client
    client = await Client.connect("localhost:7233")

    # Run a worker for the workflow
    async with Worker(
        client,
        task_queue="mutex-task-queue",
        workflows=[MutexWorkflow, SampleWorkflowWithMutex],
        activities=[signal_with_start_mutex_workflow],
    ):
        # Wait until interrupted
        print("Worker started")
        await interrupt_event.wait()
        print("Shutting down")


if __name__ == "__main__":
    asyncio.run(main())
