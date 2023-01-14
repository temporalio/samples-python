import asyncio
import logging  # noqa
import random
from typing import List
from uuid import UUID

from temporalio.client import Client
from temporalio.worker import Worker

from sticky_workers import tasks

interrupt_event = asyncio.Event()


async def main():
    # Uncomment the line below to see logging
    # logging.basicConfig(level=logging.INFO)

    # Comment line to see non-deterministic functionality
    random.seed(667)

    # Create random task queues and create parameterised workflow

    task_queues: List[str] = [str(UUID(int=random.getrandbits(128))) for _ in range(5)]

    get_available_task_queue = tasks.build_nonsticky_activity(task_queues)

    # Start client
    client = await Client.connect("localhost:7233")

    # Run a worker to distribute the workflows
    run_futures = []
    handle = Worker(
        client,
        task_queue="distribution-queue",
        workflows=[tasks.FileProcessing],
        activities=[get_available_task_queue],
    )
    run_futures.append(handle.run())
    # Wait until interrupted
    print("Base worker started")

    # Run the workers for the individual task queues
    for uuid in task_queues:
        handle = Worker(
            client,
            task_queue=uuid,
            activities=[
                tasks.download_file_to_worker_filesystem,
                tasks.work_on_file_in_worker_filesystem,
                tasks.clean_up_file_from_worker_filesystem,
            ],
        )
        run_futures.append(handle.run())
        # Wait until interrupted
        print(f"Worker {uuid} started")

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
