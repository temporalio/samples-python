from uuid import uuid4

from temporalio.client import Client
from temporalio.worker import Worker

from gcp_open_telemetry.workflow import GreetingWorkflow, compose_greeting


async def test_greeting_workflow(client: Client) -> None:
    task_queue = str(uuid4())
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[GreetingWorkflow],
        activities=[compose_greeting],
    ):
        result = await client.execute_workflow(
            GreetingWorkflow.run,
            "Temporal",
            id=str(uuid4()),
            task_queue=task_queue,
        )
        assert result == "Hello, Temporal!"
