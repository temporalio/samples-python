import uuid

from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from workflow_pause.activities import TASK_QUEUE
from workflow_pause.activities.activities import process_item
from workflow_pause.activities.workflow import ActivityPauseWorkflow


async def test_activity_workflow_retries_then_succeeds(
    client: Client, env: WorkflowEnvironment
):
    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[ActivityPauseWorkflow],
        activities=[process_item],
    ):
        result = await client.execute_workflow(
            ActivityPauseWorkflow.run,
            "widget",
            id=f"activities-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )
        assert result == "processed widget"
