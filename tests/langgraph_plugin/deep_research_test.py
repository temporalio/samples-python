"""Tests for the deep_research LangGraph sample."""

import uuid

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.worker import Worker

from langgraph_plugin.deep_research.graph import build_deep_research_graph
from langgraph_plugin.deep_research.workflow import DeepResearchWorkflow

from .conftest import requires_openai


@requires_openai
async def test_deep_research_workflow(client: Client) -> None:
    """Test deep research workflow with a research topic.

    This test requires OPENAI_API_KEY to be set.
    Note: This test may take longer due to web searches.
    """
    task_queue = f"deep-research-test-{uuid.uuid4()}"

    plugin = LangGraphPlugin(graphs={"deep_research": build_deep_research_graph})

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[DeepResearchWorkflow],
        plugins=[plugin],
    ):
        result = await client.execute_workflow(
            DeepResearchWorkflow.run,
            args=["What is Temporal.io?", 1],  # Just 1 iteration for testing
            id=f"deep-research-{uuid.uuid4()}",
            task_queue=task_queue,
        )

        # The result should contain research findings
        assert "messages" in result
