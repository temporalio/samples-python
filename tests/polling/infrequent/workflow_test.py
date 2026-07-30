import uuid

import pytest
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from polling.infrequent.activities import compose_greeting
from polling.infrequent.workflows import GreetingWorkflow


async def test_infrequent_polling_workflow(client: Client, env: WorkflowEnvironment):
    if not env.supports_time_skipping:
        pytest.skip("Too slow to test with time-skipping disabled")

    # Start a worker that hosts the workflow and activity implementations.
    task_queue = f"tq-{uuid.uuid4()}"
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[GreetingWorkflow],
        activities=[compose_greeting],
    ):
        handle = await client.start_workflow(
            GreetingWorkflow.run,
            "Temporal",
            id=f"infrequent-polling-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        result = await handle.result()
        assert result == "Hello, Temporal!"
