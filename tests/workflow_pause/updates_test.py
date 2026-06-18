import uuid

from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from workflow_pause.updates import TASK_QUEUE
from workflow_pause.updates.workflow import UpdatePauseWorkflow


async def test_update_accumulates_then_finishes(
    client: Client, env: WorkflowEnvironment
):
    async with Worker(client, task_queue=TASK_QUEUE, workflows=[UpdatePauseWorkflow]):
        handle = await client.start_workflow(
            UpdatePauseWorkflow.run,
            id=f"updates-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )
        assert await handle.execute_update(UpdatePauseWorkflow.add, 5) == 5
        assert await handle.execute_update(UpdatePauseWorkflow.add, 3) == 8
        await handle.execute_update(UpdatePauseWorkflow.finish)
        assert await handle.result() == 8
