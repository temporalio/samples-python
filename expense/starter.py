import asyncio
import uuid

from temporalio.client import Client

from .workflow import SampleExpenseWorkflow


async def main():
    # The client is a heavyweight object that should be created once per process.
    client = await Client.connect("localhost:7233")

    expense_id = str(uuid.uuid4())

    # Start the workflow (don't wait for completion)
    handle = await client.start_workflow(
        SampleExpenseWorkflow.run,
        expense_id,
        id=f"expense_{expense_id}",
        task_queue="expense",
    )

    print(f"Started workflow WorkflowID {handle.id} RunID {handle.result_run_id}")


if __name__ == "__main__":
    asyncio.run(main())
