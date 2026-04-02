"""Tests for the agentic_rag LangGraph sample."""

import uuid

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.worker import Worker

from langgraph_plugin.graph_api.agentic_rag.graph import build_agentic_rag_graph
from langgraph_plugin.graph_api.agentic_rag.workflow import AgenticRAGWorkflow

from .conftest import requires_openai


@requires_openai
async def test_agentic_rag_workflow(client: Client) -> None:
    """Test agentic RAG workflow with a knowledge base query.

    This test requires OPENAI_API_KEY to be set.
    """
    task_queue = f"agentic-rag-test-{uuid.uuid4()}"

    plugin = LangGraphPlugin(graphs={"agentic_rag": build_agentic_rag_graph})

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[AgenticRAGWorkflow],
        plugins=[plugin],
    ):
        result = await client.execute_workflow(
            AgenticRAGWorkflow.run,
            "What are AI agents?",
            id=f"agentic-rag-{uuid.uuid4()}",
            task_queue=task_queue,
        )

        # The result should contain messages with retrieved context
        assert "messages" in result
        assert len(result["messages"]) > 0
