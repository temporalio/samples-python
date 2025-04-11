import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from resource_locking.resource_allocator import ResourceAllocator
from resource_locking.lock_manager_workflow import LockManagerWorkflow
from resource_locking.resource_locking_workflow import (
    ResourceLockingWorkflow,
    use_resource,
)


async def main():
    logging.basicConfig(level=logging.INFO)

    # Start client
    client = await Client.connect("localhost:7233")

    resource_allocator = ResourceAllocator(client)

    # Run a worker for the workflow
    worker = Worker(
        client,
        task_queue="default",
        workflows=[LockManagerWorkflow, ResourceLockingWorkflow],
        activities=[
            use_resource,
            resource_allocator.send_acquire_signal,
        ],
    )

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
