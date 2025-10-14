import uuid
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client
from temporalio.worker import Worker

from openai_agents.basic.workflows.previous_response_id_workflow import (
    PreviousResponseIdWorkflow,
)


async def test_execute_workflow(client: Client):
    task_queue_name = str(uuid.uuid4())

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
