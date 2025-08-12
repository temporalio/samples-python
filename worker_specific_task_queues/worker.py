import asyncio
import logging  # noqa
import random
from typing import List
from uuid import UUID

from temporalio import activity
from temporalio.client import Client
from temporalio.worker import Worker

from worker_specific_task_queues import tasks

interrupt_event = asyncio.Event()


async def main():
    # Uncomment the line below to see logging
    # logging.basicConfig(level=logging.INFO)

    # Comment line to see non-deterministic functionality
    random.seed(667)

    # Create random task queues and build task queue selection function
    task_queue: str = (
        f"worker_specific_task_queue-host-{UUID(int=random.getrandbits(128))}"
    )

    @activity.defn(name="get_available_task_queue")
    async def select_task_queue() -> str:
        """Randomly assign the job to a queue"""
        return task_queue

    # Start client
        # Get repo root - 1 level deep from root
        repo_root = Path(__file__).resolve().parent.parent
        config_file = repo_root / "temporal.toml"
    config = ClientConfig.load_client_connect_config(config_file=str(config_file))
    config["target_host"] = "localhost:7233"
    client = await Client.connect(**config)

    # Run a worker to distribute the workflows
    run_futures = []
    handle = Worker(
        client,
        task_queue="worker_specific_task_queue-distribution-queue",
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
