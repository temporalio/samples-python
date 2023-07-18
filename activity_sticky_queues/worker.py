import asyncio
import logging  # noqa
import random
from typing import List
from uuid import UUID

from temporalio import activity
from temporalio.client import Client
from temporalio.worker import Worker

from activity_sticky_queues import tasks

interrupt_event = asyncio.Event()


async def main():
    # Uncomment the line below to see logging
    # logging.basicConfig(level=logging.INFO)

    # Comment line to see non-deterministic functionality
    random.seed(667)

    # Create random task queues and build task queue selection function
    task_queue: str = f"activity_sticky_queue-host-{UUID(int=random.getrandbits(128))}"

    @activity.defn(name="get_available_task_queue")
    async def select_task_queue() -> str:
        """Randomly assign the job to a queue"""
        return task_queue

    # Start client
    client = await Client.connect("localhost:7233")

    # Run a worker to distribute the workflows
    run_futures = []
    handle = Worker(
        client,
        task_queue="activity_sticky_queue-distribution-queue",
        workflows=[tasks.FileProcessing],
        activities=[select_task_queue],
    )
    run_futures.append(handle.run())
    print("Base worker started")

    # Run unique task queue for this particular host
    handle = Worker(
        client,
        task_queue=task_queue,
        activities=[
            tasks.download_file_to_worker_filesystem,
            tasks.work_on_file_in_worker_filesystem,
            tasks.clean_up_file_from_worker_filesystem,
        ],
    )
    run_futures.append(handle.run())
    # Wait until interrupted
    print(f"Worker {task_queue} started")

    print("All workers started, ctrl+c to exit")
    await asyncio.gather(*run_futures)


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
        print("\nShutting down workers")
