import asyncio

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

    # No network call here
    transaction = client.start_workflow(
        TransactionWorkflow.run,
        args=[TransactionRequest(amount=77.7)],
        id="transaction-abc123",
        task_queue=TASK_QUEUE,
        lazy=True,
    )

    # Send the MultiOp gRPC
    confirmation_token = await transaction.execute_update(
        TransactionWorkflow.get_confirmation
    )
    final_report = await transaction.result()

    print(f"got confirmation token: {confirmation_token}")
    print(f"got final report: {final_report}")


async def use_a_lock_service():
    client = await Client.connect("localhost:7233")

    # The user wants to acquire a lock lease from a lock service

    lock_service = client.start_workflow(
        LockService.run,
        id="lock-service-id",
        task_queue="uws",
        lazy=True,
    )

    lock = await lock_service.execute_update(LockService.acquire_lock)
    print(f"acquired lock: {lock}")


async def main():
    await financial_transaction_with_early_return()
    await use_a_lock_service()


if __name__ == "__main__":
    asyncio.run(main())
