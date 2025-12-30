"""Tests for the reflection LangGraph sample."""

import uuid

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.worker import Worker

from langgraph_samples.reflection.graph import build_reflection_graph
from langgraph_samples.reflection.workflow import ReflectionWorkflow

from .conftest import requires_openai


@requires_openai
async def test_reflection_workflow(client: Client) -> None:
    """Test reflection workflow with a writing task.

    This test requires OPENAI_API_KEY to be set.
    """
    task_queue = f"reflection-test-{uuid.uuid4()}"

    plugin = LangGraphPlugin(graphs={"reflection": build_reflection_graph})

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[ReflectionWorkflow],
        plugins=[plugin],
    ):
        result = await client.execute_workflow(
            ReflectionWorkflow.run,
            args=["Write a short haiku about programming", 2],
            id=f"reflection-{uuid.uuid4()}",
            task_queue=task_queue,
        )

        # The result should contain final content
        assert "final_content" in result or "current_draft" in result
        assert "messages" in result
