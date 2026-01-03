"""Tests for the agentic_rag Functional API sample."""

import uuid

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.worker import Worker

from langgraph_plugin.functional_api.agentic_rag.entrypoint import (
    agentic_rag_entrypoint,
)
from langgraph_plugin.functional_api.agentic_rag.workflow import AgenticRagWorkflow


async def test_agentic_rag_functional_workflow(client: Client) -> None:
    """Test that the agentic RAG functional workflow retrieves and generates."""
    task_queue = f"agentic-rag-functional-test-{uuid.uuid4()}"

    plugin = LangGraphPlugin(
        graphs={"agentic_rag_entrypoint": agentic_rag_entrypoint},
    )

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[AgenticRagWorkflow],
        plugins=[plugin],
    ):
        result = await client.execute_workflow(
            AgenticRagWorkflow.run,
            "What is Temporal?",
            id=f"agentic-rag-functional-{uuid.uuid4()}",
            task_queue=task_queue,
        )

        assert "answer" in result
        assert "documents_used" in result
