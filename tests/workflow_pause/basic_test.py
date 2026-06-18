import uuid

from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from workflow_pause.basic import TASK_QUEUE
from workflow_pause.basic.workflow import BasicPauseWorkflow


async def test_basic_workflow_completes(client: Client, env: WorkflowEnvironment):
    async with Worker(client, task_queue=TASK_QUEUE, workflows=[BasicPauseWorkflow]):
        result = await client.execute_workflow(
            BasicPauseWorkflow.run,
            3,
            id=f"basic-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )
        assert result == 3
