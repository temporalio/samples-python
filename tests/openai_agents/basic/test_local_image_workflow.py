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

from openai_agents.basic.activities.image_activities import read_image_as_base64
from openai_agents.basic.workflows.local_image_workflow import LocalImageWorkflow


def local_image_test_model():
    return TestModel.returning_responses(
        [ResponseBuilders.output_message("I can see a bison in the image.")]
    )


@pytest.mark.parametrize("mock_model", [True, False])
async def test_execute_workflow_default_question(client: Client, mock_model: bool):
    task_queue_name = str(uuid.uuid4())
    if not mock_model and not os.environ.get("OPENAI_API_KEY"):
        pytest.skip(
            f"Skipping test (mock_model={mock_model}), because OPENAI_API_KEY is not set"
        )

    async with AgentEnvironment(
        model=local_image_test_model() if mock_model else None
    ) as agent_env:
        client = agent_env.applied_on_client(client)
        async with Worker(
            client,
            task_queue=task_queue_name,
            workflows=[LocalImageWorkflow],
            activity_executor=ThreadPoolExecutor(5),
            activities=[read_image_as_base64],
        ):
            result = await client.execute_workflow(
                LocalImageWorkflow.run,
                "openai_agents/basic/media/image_bison.jpg",  # Path to test image
                id=str(uuid.uuid4()),
                task_queue=task_queue_name,
            )

            # Verify the result is a string response
            assert isinstance(result, str)
            assert len(result) > 0


@pytest.mark.parametrize("mock_model", [True, False])
async def test_execute_workflow_custom_question(client: Client, mock_model: bool):
    task_queue_name = str(uuid.uuid4())
    if not mock_model and not os.environ.get("OPENAI_API_KEY"):
        pytest.skip(
            f"Skipping test (mock_model={mock_model}), because OPENAI_API_KEY is not set"
        )

    async with AgentEnvironment(
        model=local_image_test_model() if mock_model else None
    ) as agent_env:
        client = agent_env.applied_on_client(client)
        async with Worker(
            client,
            task_queue=task_queue_name,
            workflows=[LocalImageWorkflow],
            activity_executor=ThreadPoolExecutor(5),
            activities=[read_image_as_base64],
        ):
            custom_question = "What animals do you see in this image?"
            result = await client.execute_workflow(
                LocalImageWorkflow.run,
                args=["openai_agents/basic/media/image_bison.jpg", custom_question],
                id=str(uuid.uuid4()),
                task_queue=task_queue_name,
            )

            # Verify the result is a string response
            assert isinstance(result, str)
            assert len(result) > 0
