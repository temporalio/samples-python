"""Tests for the plan_and_execute Functional API sample."""

import uuid

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.worker import Worker

from langgraph_plugin.functional_api.plan_and_execute.entrypoint import (
    plan_execute_entrypoint,
)
from langgraph_plugin.functional_api.plan_and_execute.workflow import (
    PlanExecuteWorkflow,
)


async def test_plan_execute_functional_workflow(client: Client) -> None:
    """Test that the plan-and-execute functional workflow creates and executes a plan."""
    task_queue = f"plan-execute-functional-test-{uuid.uuid4()}"

    plugin = LangGraphPlugin(
        graphs={"plan_execute_entrypoint": plan_execute_entrypoint},
    )

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[PlanExecuteWorkflow],
        plugins=[plugin],
    ):
        result = await client.execute_workflow(
            PlanExecuteWorkflow.run,
            "Build a simple calculator",
            id=f"plan-execute-functional-{uuid.uuid4()}",
            task_queue=task_queue,
        )

        assert "final_response" in result
        assert "step_results" in result
        assert len(result["step_results"]) > 0
