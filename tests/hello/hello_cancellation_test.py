import asyncio
import uuid

from temporalio.api.common.v1 import WorkflowExecution
from temporalio.api.workflowservice.v1 import (
    DescribeWorkflowExecutionRequest,
    DescribeWorkflowExecutionResponse,
)
from temporalio.client import Client, WorkflowExecutionStatus, WorkflowFailureError
from temporalio.worker import Worker

from hello.hello_cancellation import (
    CancellationWorkflow,
    cleanup_activity,
    never_complete_activity,
)


async def test_cancel_workflow(client: Client):
    task_queue_name = str(uuid.uuid4())

    async with Worker(
        client,
        task_queue=task_queue_name,
        workflows=[CancellationWorkflow],
        activities=[cleanup_activity, never_complete_activity],
    ):
        workflow_id = str(uuid.uuid4())
        handle = await client.start_workflow(
            CancellationWorkflow.run,
            id=workflow_id,
            task_queue=task_queue_name,
        )

        await asyncio.wait_for(
            wait_for_activity_to_start("never_complete_activity", client, workflow_id),
            timeout=5,
        )

        await handle.cancel()

        await asyncio.wait_for(
            wait_for_workflow_to_has_status(
                WorkflowExecutionStatus.CANCELED, client, workflow_id
            ),
            timeout=5,
        )

        assert WorkflowExecutionStatus.CANCELED == (await handle.describe()).status


async def wait_for_activity_to_start(activity_name, client, workflow_id):
    while not (await has_activity_started(activity_name, workflow_id, client)):
        await asyncio.sleep(0.2)


async def has_activity_started(activity_name, workflow_id, client):
    response: DescribeWorkflowExecutionResponse = await describe_workflow(
        client, workflow_id
    )

    for pending_activity in response.pending_activities:
        if pending_activity.activity_type.name == activity_name:
            return True

    return False


async def wait_for_workflow_to_has_status(status, client, workflow_id):
    while not (await has_workflow_status(status, workflow_id, client)):
        await asyncio.sleep(0.2)


async def has_workflow_status(status, workflow_id, client):
    response: DescribeWorkflowExecutionResponse = await describe_workflow(
        client, workflow_id
    )
    return response.workflow_execution_info.status == status


async def describe_workflow(client, workflow_id):
    return await client.workflow_service.describe_workflow_execution(
        DescribeWorkflowExecutionRequest(
            namespace=client.namespace,
            execution=WorkflowExecution(workflow_id=workflow_id),
        )
    )
