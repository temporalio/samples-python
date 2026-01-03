"""Tests for the deep_research Functional API sample."""

import uuid

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.worker import Worker

from langgraph_plugin.functional_api.deep_research.entrypoint import (
    deep_research_entrypoint,
)
from langgraph_plugin.functional_api.deep_research.workflow import DeepResearchWorkflow


async def test_deep_research_functional_workflow(client: Client) -> None:
    """Test that the deep research functional workflow produces a report."""
    task_queue = f"deep-research-functional-test-{uuid.uuid4()}"

    plugin = LangGraphPlugin(
        graphs={"deep_research_entrypoint": deep_research_entrypoint},
    )

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[DeepResearchWorkflow],
        plugins=[plugin],
    ):
        result = await client.execute_workflow(
            DeepResearchWorkflow.run,
            "Python async programming",
            id=f"deep-research-functional-{uuid.uuid4()}",
            task_queue=task_queue,
        )

        assert "report" in result
        assert "relevant_results" in result
        assert result["relevant_results"] >= 0
