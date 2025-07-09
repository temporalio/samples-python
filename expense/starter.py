import argparse
import asyncio
import uuid

from temporalio.client import Client

from .workflow import SampleExpenseWorkflow


async def main():
    parser = argparse.ArgumentParser(description="Start an expense workflow")
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for workflow completion (default: start and return immediately)",
    )
    parser.add_argument(
        "--expense-id",
        type=str,
        help="Expense ID to use (default: generate random UUID)",
    )
    args = parser.parse_args()

    # The client is a heavyweight object that should be created once per process.
    client = await Client.connect("localhost:7233")

    expense_id = args.expense_id or str(uuid.uuid4())
    workflow_id = f"expense_{expense_id}"

    # Start the workflow
    handle = await client.start_workflow(
        SampleExpenseWorkflow.run,
        expense_id,
        id=workflow_id,
        task_queue="expense",
    )

    print(f"Started workflow WorkflowID {handle.id} RunID {handle.result_run_id}")
    print(f"Workflow will register itself with UI system for expense {expense_id}")

    if args.wait:
        print("Waiting for workflow to complete...")
        result = await handle.result()
        print(f"Workflow completed with result: {result}")
        return result
    else:
        print("Workflow started. Use --wait flag to wait for completion.")
        return None


if __name__ == "__main__":
    asyncio.run(main())
