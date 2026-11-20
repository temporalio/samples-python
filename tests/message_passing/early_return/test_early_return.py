import asyncio
import uuid

from temporalio import activity, common
from temporalio.client import Client, WithStartWorkflowOperation
from temporalio.worker import Worker

from message_passing.update_with_start.early_return.activities import (
    PaymentAuthorization,
    PaymentDetails,
)
from message_passing.update_with_start.early_return.workflows import PaymentWorkflow


async def test_update_result_arrives_before_workflow_completes(client: Client) -> None:
    task_queue = f"early-return-{uuid.uuid4()}"
    capture_started = asyncio.Event()
    release_capture = asyncio.Event()

    @activity.defn(name="authorize_payment")
    async def authorize_payment(details: PaymentDetails) -> PaymentAuthorization:
        return PaymentAuthorization(id="test-authorization", amount=details.amount)

    @activity.defn(name="capture_payment")
    async def capture_payment(authorization: PaymentAuthorization) -> None:
        capture_started.set()
        await release_capture.wait()

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[PaymentWorkflow],
        activities=[authorize_payment, capture_payment],
    ):
        start_operation = WithStartWorkflowOperation(
            PaymentWorkflow.run,
            PaymentDetails(amount=500),
            id=f"early-return-{uuid.uuid4()}",
            id_conflict_policy=common.WorkflowIDConflictPolicy.FAIL,
            task_queue=task_queue,
        )

        authorization = await client.execute_update_with_start_workflow(
            PaymentWorkflow.wait_until_authorized,
            start_workflow_operation=start_operation,
        )
        workflow_handle = await start_operation.workflow_handle()
        workflow_result = asyncio.create_task(workflow_handle.result())

        await capture_started.wait()
        await asyncio.sleep(0)

        assert authorization == PaymentAuthorization(
            id="test-authorization", amount=500
        )
        assert workflow_result.done() is False

        release_capture.set()
        assert await workflow_result == authorization
