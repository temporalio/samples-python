import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from resource_locking.load_workflow import LoadWorkflow, load
from resource_locking.sem_workflow import SemaphoreWorkflow

async def main():
    # Uncomment the line below to see logging
    logging.basicConfig(level=logging.INFO)

    # Start client
    client = await Client.connect("localhost:7233")

    # Run a worker for the workflow
    worker = Worker(
        client,
        task_queue="default",
        workflows=[SemaphoreWorkflow, LoadWorkflow],
        activities=[load],
    )

    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
