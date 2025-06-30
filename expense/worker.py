import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from .activities import (
    cleanup_http_client,
    create_expense_activity,
    initialize_http_client,
    payment_activity,
    register_for_decision_activity,
)
from .workflow import SampleExpenseWorkflow


async def main():
    # The client and worker are heavyweight objects that should be created once per process.
    client = await Client.connect("localhost:7233")

    # Initialize HTTP client before starting worker
    await initialize_http_client()

    try:
        # Run the worker
        worker = Worker(
            client,
            task_queue="expense",
            workflows=[SampleExpenseWorkflow],
            activities=[
                create_expense_activity,
                register_for_decision_activity,
                payment_activity,
            ],
        )

        print("Worker starting...")
        await worker.run()
    finally:
        # Cleanup HTTP client when worker shuts down
        await cleanup_http_client()


if __name__ == "__main__":
    asyncio.run(main())
