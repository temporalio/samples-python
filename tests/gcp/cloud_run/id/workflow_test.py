import uuid

from temporalio.client import Client
from temporalio.worker import Worker

from gcp.cloud_run.id.activities import compose_greeting
from gcp.cloud_run.id.workflows import GreetingWorkflow


async def test_greeting_workflow(client: Client):
    task_queue_name = str(uuid.uuid4())

    async with Worker(
        client,
        task_queue=task_queue_name,
        workflows=[GreetingWorkflow],
        activities=[compose_greeting],
    ):
        result = await client.execute_workflow(
            GreetingWorkflow.run,
            "Temporal",
            id=str(uuid.uuid4()),
            task_queue=task_queue_name,
        )
        assert result == "Hello, Temporal!"
