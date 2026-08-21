import uuid

from temporalio.client import Client
from temporalio.worker import Worker

from gcp_cloud_run.workflow import GreetingWorkflow, compose_greeting


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
