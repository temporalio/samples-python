import uuid

from temporalio.client import Client
from temporalio.worker import Worker

from cloud_run_worker.activities import hello_activity
from cloud_run_worker.workflows import SampleWorkflow


async def test_execute_workflow(client: Client):
    task_queue_name = str(uuid.uuid4())

    async with Worker(
        client,
        task_queue=task_queue_name,
        workflows=[SampleWorkflow],
        activities=[hello_activity],
    ):
        result = await client.execute_workflow(
            SampleWorkflow.run,
            "World",
            id=str(uuid.uuid4()),
            task_queue=task_queue_name,
        )

    assert result == "Hello, World!"
