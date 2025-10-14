import uuid
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client
from temporalio.worker import Worker

from openai_agents.basic.workflows.non_strict_output_workflow import (
    NonStrictOutputWorkflow,
)


async def test_execute_workflow(client: Client):
    task_queue_name = str(uuid.uuid4())

    async with Worker(
        client,
        task_queue=task_queue_name,
        workflows=[NonStrictOutputWorkflow],
        activity_executor=ThreadPoolExecutor(5),
        # No external activities needed
    ):
        result = await client.execute_workflow(
            NonStrictOutputWorkflow.run,
            "Tell me 3 funny jokes about programming.",
            id=str(uuid.uuid4()),
            task_queue=task_queue_name,
        )

        # Verify the result has the expected structure
        assert isinstance(result, dict)

        assert "strict_error" in result
        assert "non_strict_result" in result

        # If there's a strict_error, it should be a string
        if "strict_error" in result:
            assert isinstance(result["strict_error"], str)
            assert len(result["strict_error"]) > 0

        jokes = result["non_strict_result"]["jokes"]
        assert isinstance(jokes, dict)
        assert isinstance(jokes[list(jokes.keys())[0]], str)
