import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from .activities import create_expense_activity, payment_activity, wait_for_decision_activity
from .workflow import SampleExpenseWorkflow


async def main():
    # The client and worker are heavyweight objects that should be created once per process.
    client = await Client.connect("localhost:7233")

    # Run the worker
    worker = Worker(
        client,
        task_queue="expense",
        workflows=[SampleExpenseWorkflow],
        activities=[
            create_expense_activity,
            wait_for_decision_activity,
            payment_activity,
        ],
    )

    print("Worker starting...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main()) 