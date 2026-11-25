import asyncio
import uuid

from temporalio import common
from temporalio.client import Client, WithStartWorkflowOperation
from temporalio.envconfig import ClientConfig

from message_passing.update_with_start.early_return import TASK_QUEUE
from message_passing.update_with_start.early_return.activities import PaymentDetails
from message_passing.update_with_start.early_return.workflows import PaymentWorkflow


async def main() -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    payment_id = f"payment-{uuid.uuid4()}"
    start_operation = WithStartWorkflowOperation(
        PaymentWorkflow.run,
        PaymentDetails(amount=500),
        id=payment_id,
        id_conflict_policy=common.WorkflowIDConflictPolicy.FAIL,
        task_queue=TASK_QUEUE,
    )

    authorization = await client.execute_update_with_start_workflow(
        PaymentWorkflow.wait_until_authorized,
        start_workflow_operation=start_operation,
    )
    workflow_handle = await start_operation.workflow_handle()

    print(
        f"Payment {workflow_handle.id} was authorized as {authorization.id}. "
        "Capture will continue in the Workflow."
    )


if __name__ == "__main__":
    asyncio.run(main())
