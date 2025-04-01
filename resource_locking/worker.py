import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from resource_locking.resource_locking_workflow import ResourceLockingWorkflow, use_resource
from resource_locking.lock_manager_workflow import LockManagerWorkflow

async def main():
    # Uncomment the line below to see logging
    logging.basicConfig(level=logging.INFO)

    # Start client
    client = await Client.connect("localhost:7233")

    # Run a worker for the workflow
    worker = Worker(
        client,
        task_queue="default",
        workflows=[LockManagerWorkflow, ResourceLockingWorkflow],
        activities=[use_resource],
    )

    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
