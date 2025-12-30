"""Tests for the supervisor LangGraph sample."""

import uuid

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.worker import Worker

from langgraph_samples.supervisor.graph import build_supervisor_graph
from langgraph_samples.supervisor.workflow import SupervisorWorkflow

from .conftest import requires_openai


@requires_openai
async def test_supervisor_workflow(client: Client) -> None:
    """Test supervisor workflow with a research query.

    This test requires OPENAI_API_KEY to be set.
    """
    task_queue = f"supervisor-test-{uuid.uuid4()}"

    plugin = LangGraphPlugin(graphs={"supervisor": build_supervisor_graph})

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[SupervisorWorkflow],
        plugins=[plugin],
    ):
        result = await client.execute_workflow(
            SupervisorWorkflow.run,
            "What is the capital of France?",
            id=f"supervisor-{uuid.uuid4()}",
            task_queue=task_queue,
        )

        # The result should contain messages
        assert "messages" in result
        assert len(result["messages"]) > 0
