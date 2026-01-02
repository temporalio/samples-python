"""Tests for the plan_and_execute LangGraph sample."""

import uuid

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.worker import Worker

from langgraph_plugin.graph_api.plan_and_execute.graph import build_plan_and_execute_graph
from langgraph_plugin.graph_api.plan_and_execute.workflow import PlanAndExecuteWorkflow

from .conftest import requires_openai


@requires_openai
async def test_plan_and_execute_workflow(client: Client) -> None:
    """Test plan and execute workflow with a simple task.

    This test requires OPENAI_API_KEY to be set.
    """
    task_queue = f"plan-execute-test-{uuid.uuid4()}"

    plugin = LangGraphPlugin(graphs={"plan_and_execute": build_plan_and_execute_graph})

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[PlanAndExecuteWorkflow],
        plugins=[plugin],
    ):
        result = await client.execute_workflow(
            PlanAndExecuteWorkflow.run,
            "Calculate 15 * 8 and tell me the result",
            id=f"plan-execute-{uuid.uuid4()}",
            task_queue=task_queue,
        )

        # The result should contain plan steps and results
        assert "messages" in result
