import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from temporalio.client import Client
from temporalio.contrib.openai_agents.testing import (
    AgentEnvironment,
    ResponseBuilders,
    TestModel,
)
from temporalio.worker import Worker

from openai_agents.basic.workflows.hello_world_workflow import HelloWorldAgent


def hello_world_test_model():
    return TestModel.returning_responses(
        [ResponseBuilders.output_message("This is a haiku (not really)")]
    )


@pytest.mark.parametrize("mock_model", [True, False])
async def test_execute_workflow(client: Client, mock_model: bool):
    task_queue_name = str(uuid.uuid4())
    if not mock_model and not os.environ.get("OPENAI_API_KEY"):
        pytest.skip(
            f"Skipping test (mock_model={mock_model}), because OPENAI_API_KEY is not set"
        )

    async with AgentEnvironment(
        model=hello_world_test_model() if mock_model else None
    ) as agent_env:
        client = agent_env.applied_on_client(client)
        async with Worker(
            client,
            task_queue=task_queue_name,
            workflows=[HelloWorldAgent],
            activity_executor=ThreadPoolExecutor(5),
        ):
            result = await client.execute_workflow(
                HelloWorldAgent.run,
                "Write a recursive haiku about recursive haikus.",
                id=str(uuid.uuid4()),
                task_queue=task_queue_name,
            )

            if mock_model:
                assert result == "This is a haiku (not really)"
            else:
                assert isinstance(result, str)
                assert len(result) > 0
