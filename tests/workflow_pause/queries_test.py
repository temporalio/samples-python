import uuid

from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from workflow_pause.queries import TASK_QUEUE
from workflow_pause.queries.workflow import QueryPauseWorkflow


async def test_query_returns_count(client: Client, env: WorkflowEnvironment):
    async with Worker(client, task_queue=TASK_QUEUE, workflows=[QueryPauseWorkflow]):
        result = await client.execute_workflow(
            QueryPauseWorkflow.run,
            2,
            id=f"queries-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )
        assert result == 2
