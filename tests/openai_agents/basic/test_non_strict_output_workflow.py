import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
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

        # Should have either strict_result or strict_error
        assert "strict_result" in result or "strict_error" in result

        # Should have either non_strict_result or non_strict_error
        assert "non_strict_result" in result or "non_strict_error" in result

        # If there's a strict_error, it should be a string
        if "strict_error" in result:
            assert isinstance(result["strict_error"], str)
            assert len(result["strict_error"]) > 0

        # If there's a non_strict_result, verify it's valid
        if "non_strict_result" in result:
            assert result["non_strict_result"] is not None
