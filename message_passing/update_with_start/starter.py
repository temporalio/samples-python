import asyncio

from temporalio import common
from temporalio.client import Client

from message_passing.update_with_start import TASK_QUEUE
from message_passing.update_with_start.workflows import (
    LockService,
    TransactionRequest,
    TransactionWorkflow,
)


async def financial_transaction_with_early_return():
    client = await Client.connect("localhost:7233")
    # The user wants to kick off a long-running transaction workflow and get an early-return result.

    confirmation_token = await client.start_workflow(
        TransactionWorkflow.run,
        args=[TransactionRequest(amount=77.7)],
        id="transaction-abc123",
        task_queue=TASK_QUEUE,
        continuation=lambda wf_handle: wf_handle.execute_update(
            # The wf_handle is trapped because Python doesn't support multi-statement anonymous functions.
            TransactionWorkflow.get_confirmation
        ),
    )

    print(f"got confirmation token: {confirmation_token}")

    # ❗❗ But we can't get the workflow handle if we use a lambda above
    # final_report = await wf_handle.result()
    # print(f"got final report: {final_report}")


async def use_a_lock_service():
    client = await Client.connect("localhost:7233")

    # The user wants to acquire a lock lease from a lock service

    lock = await client.start_workflow(
        LockService.run,
        id="lock-service-id",
        id_conflict_policy=common.WorkflowIDConflictPolicy.USE_EXISTING,
        task_queue="uws",
        continuation=lambda wf_handle: wf_handle.execute_update(
            LockService.acquire_lock
        ),
    )

    print(f"acquired lock: {lock}")


async def main():
    await financial_transaction_with_early_return()
    await use_a_lock_service()


if __name__ == "__main__":
    asyncio.run(main())
