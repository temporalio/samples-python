"""Tests for the reflection Functional API sample."""

import uuid

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphFunctionalPlugin
from temporalio.worker import Worker

from langgraph_plugin.functional_api.reflection.entrypoint import reflection_entrypoint
from langgraph_plugin.functional_api.reflection.workflow import ReflectionWorkflow


async def test_reflection_functional_workflow(client: Client) -> None:
    """Test that the reflection functional workflow improves content."""
    task_queue = f"reflection-functional-test-{uuid.uuid4()}"

    plugin = LangGraphFunctionalPlugin(
        entrypoints={"reflection_entrypoint": reflection_entrypoint},
    )

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[ReflectionWorkflow],
        plugins=[plugin],
    ):
        result = await client.execute_workflow(
            ReflectionWorkflow.run,
            "Write about testing",
            id=f"reflection-functional-{uuid.uuid4()}",
            task_queue=task_queue,
        )

        assert "content" in result
        assert "iterations" in result
        assert result["iterations"] >= 1
