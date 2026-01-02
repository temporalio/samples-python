"""Tests for the supervisor Functional API sample."""

import uuid

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphFunctionalPlugin
from temporalio.worker import Worker

from langgraph_plugin.functional_api.supervisor.entrypoint import supervisor_entrypoint
from langgraph_plugin.functional_api.supervisor.workflow import SupervisorWorkflow


async def test_supervisor_functional_workflow(client: Client) -> None:
    """Test that the supervisor functional workflow coordinates agents."""
    task_queue = f"supervisor-functional-test-{uuid.uuid4()}"

    plugin = LangGraphFunctionalPlugin(
        entrypoints={"supervisor_entrypoint": supervisor_entrypoint},
    )

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[SupervisorWorkflow],
        plugins=[plugin],
    ):
        result = await client.execute_workflow(
            SupervisorWorkflow.run,
            "Analyze market trends",
            id=f"supervisor-functional-{uuid.uuid4()}",
            task_queue=task_queue,
        )

        assert "final_answer" in result
        assert "agent_outputs" in result
        assert len(result["agent_outputs"]) > 0
