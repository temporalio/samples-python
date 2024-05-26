import uuid

from temporalio.client import Client, WorkflowExecutionStatus
from temporalio.worker import Worker

from hello.hello_update import GreetingWorkflow


async def test_signal_workflow(client: Client):
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
        assert WorkflowExecutionStatus.COMPLETED == (await handle.describe()).status
