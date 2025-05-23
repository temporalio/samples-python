import uuid

import pytest
from temporalio.client import Client, WorkflowExecutionStatus
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from hello.hello_update import GreetingWorkflow


async def test_update_workflow(client: Client, env: WorkflowEnvironment):
    task_queue_name = str(uuid.uuid4())
    async with Worker(client, task_queue=task_queue_name, workflows=[GreetingWorkflow]):
        handle = await client.start_workflow(
            GreetingWorkflow.run, id=str(uuid.uuid4()), task_queue=task_queue_name
        )

        assert WorkflowExecutionStatus.RUNNING == (await handle.describe()).status

        update_result = await handle.execute_update(
            GreetingWorkflow.update_workflow_status
        )
        assert "Workflow status updated" == update_result
        assert "Hello, World!" == (await handle.result())
        assert WorkflowExecutionStatus.COMPLETED == (await handle.describe()).status
