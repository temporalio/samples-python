import uuid
import pytest
import os
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client
from temporalio.contrib.openai_agents.testing import (
    AgentEnvironment,
    ResponseBuilders,
    TestModel,
)
from temporalio.worker import Worker

from openai_agents.basic.activities.get_weather_activity import get_weather
from openai_agents.basic.workflows.tools_workflow import ToolsWorkflow


def tools_test_model():
    return TestModel.returning_responses(
        [
            ResponseBuilders.tool_call('{"city": "New York"}', "get_weather"),
            ResponseBuilders.output_message(
                "The weather in New York is sunny with a temperature of 75°F."
            ),
        ]
    )


@pytest.mark.parametrize("mock_model", [True, False])
async def test_execute_workflow(client: Client, mock_model: bool):
    task_queue_name = str(uuid.uuid4())
    if not mock_model and not os.environ.get("OPENAI_API_KEY"):
        pytest.skip(
            f"Skipping test (mock_model={mock_model}), because OPENAI_API_KEY is not set"
        )

    async with AgentEnvironment(
        model=tools_test_model() if mock_model else None
    ) as agent_env:
        client = agent_env.applied_on_client(client)
        async with Worker(
            client,
            task_queue=task_queue_name,
            workflows=[ToolsWorkflow],
            activity_executor=ThreadPoolExecutor(5),
            activities=[get_weather],
        ):
            result = await client.execute_workflow(
                ToolsWorkflow.run,
                "What's the weather like in New York?",
                id=str(uuid.uuid4()),
                task_queue=task_queue_name,
            )

            # Verify the result is a string response
            assert isinstance(result, str)
            assert len(result) > 0
