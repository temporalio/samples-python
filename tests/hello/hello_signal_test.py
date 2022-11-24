import uuid

from temporalio.client import Client, WorkflowExecutionStatus
from temporalio.worker import Worker

from hello.hello_signal import GreetingWorkflow


async def test_signal_workflow(client: Client):
    task_queue_name = str(uuid.uuid4())
    async with Worker(client, task_queue=task_queue_name, workflows=[GreetingWorkflow]):
        handle = await client.start_workflow(
            GreetingWorkflow.run, id=str(uuid.uuid4()), task_queue=task_queue_name
        )

        await handle.signal(GreetingWorkflow.submit_greeting, "user1")
        await handle.signal(GreetingWorkflow.submit_greeting, "user2")
        assert WorkflowExecutionStatus.RUNNING == (await handle.describe()).status

        await handle.signal(GreetingWorkflow.exit)
        assert ["Hello, user1", "Hello, user2"] == await handle.result()
        assert WorkflowExecutionStatus.COMPLETED == (await handle.describe()).status
