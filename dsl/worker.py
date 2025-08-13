import asyncio
import logging

from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile
from temporalio.worker import Worker

from dsl.activities import DSLActivities
from dsl.workflow import DSLWorkflow

interrupt_event = asyncio.Event()


async def main():
    # Connect client
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    # Run a worker for the activities and workflow
    activities = DSLActivities()
    async with Worker(
        client,
        task_queue="dsl-task-queue",
        activities=[
            activities.activity1,
            activities.activity2,
            activities.activity3,
            activities.activity4,
            activities.activity5,
        ],
        workflows=[DSLWorkflow],
    ):
        # Wait until interrupted
        logging.info("Worker started, ctrl+c to exit")
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
