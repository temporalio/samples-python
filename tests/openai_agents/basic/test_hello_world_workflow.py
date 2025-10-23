import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from agents import ModelResponse, Usage
from openai.types.responses import ResponseOutputMessage, ResponseOutputText
from temporalio.client import Client
from temporalio.worker import Worker

from openai_agents.basic.workflows.hello_world_workflow import HelloWorldAgent
from tests.openai_agents.conftest import sequential_test_model


@pytest.fixture
def test_model():
    return sequential_test_model(
        [
            ModelResponse(
                output=[
                    ResponseOutputMessage(
                        id="1",
                        content=[
                            ResponseOutputText(
                                annotations=[],
                                text="This is a haiku (not really)",
                                type="output_text",
                            )
                        ],
                        role="assistant",
                        status="completed",
                        type="message",
                    )
                ],
                usage=Usage(
                    requests=1, input_tokens=1, output_tokens=1, total_tokens=1
                ),
                response_id="1",
            )
        ]
    )


@pytest.fixture
def test_model():
    return TestModel.returning_responses(
        [ResponseBuilders.output_message("This is a haiku (not really)")]
    )


async def test_execute_workflow(client: Client):
    task_queue_name = str(uuid.uuid4())

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
        assert isinstance(result, str)
        assert len(result) > 0
