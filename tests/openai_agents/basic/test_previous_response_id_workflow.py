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

from openai_agents.basic.workflows.previous_response_id_workflow import (
    PreviousResponseIdWorkflow,
)


def previous_response_id_test_model():
    return TestModel.returning_responses(
        [
            ResponseBuilders.output_message("The capital of France is Paris."),
            ResponseBuilders.output_message(
                "Paris has a population of approximately 2.1 million people within the city proper."
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
        model=previous_response_id_test_model() if mock_model else None
    ) as agent_env:
        client = agent_env.applied_on_client(client)
        async with Worker(
            client,
            task_queue=task_queue_name,
            workflows=[PreviousResponseIdWorkflow],
            activity_executor=ThreadPoolExecutor(5),
        ):
            first_question = "What is the capital of France?"
            follow_up_question = "What is the population of that city?"

            result = await client.execute_workflow(
                PreviousResponseIdWorkflow.run,
                args=[first_question, follow_up_question],
                id=str(uuid.uuid4()),
                task_queue=task_queue_name,
            )

            # Verify the result is a tuple with two string responses
            assert isinstance(result, tuple)
            assert len(result) == 2

            first_response, second_response = result
            assert isinstance(first_response, str)
            assert isinstance(second_response, str)
            assert len(first_response) > 0
            assert len(second_response) > 0

            # The responses should be different (not identical)
            assert first_response != second_response
