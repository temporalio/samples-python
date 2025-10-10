import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from temporalio.client import Client
from temporalio.worker import Worker

from openai_agents.basic.workflows.agent_lifecycle_workflow import (
    AgentLifecycleWorkflow,
)


async def test_execute_workflow(client: Client):
    task_queue_name = str(uuid.uuid4())

    async with Worker(
        client,
        task_queue=task_queue_name,
        workflows=[AgentLifecycleWorkflow],
        activity_executor=ThreadPoolExecutor(5),
        # No external activities needed - workflow uses function tools
    ):
        result = await client.execute_workflow(
            AgentLifecycleWorkflow.run,
            10,  # max_number parameter
            id=str(uuid.uuid4()),
            task_queue=task_queue_name,
        )

        # Verify the result has the expected structure
        assert hasattr(result, "number")
        assert isinstance(result.number, int)
        assert (
            0 <= result.number <= 20
        )  # Should be between 0 and max*2 due to multiply operation
