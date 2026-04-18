import uuid

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.worker import Worker

from langgraph_plugin.functional_api.react_agent.workflow import (
    ReactAgentFunctionalWorkflow,
    activity_options,
    all_tasks,
)


async def test_functional_react_agent(client: Client) -> None:
    task_queue = f"functional-react-agent-test-{uuid.uuid4()}"
    plugin = LangGraphPlugin(
        tasks=all_tasks,
        activity_options=activity_options,
    )

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[ReactAgentFunctionalWorkflow],
        plugins=[plugin],
    ):
        result = await client.execute_workflow(
            ReactAgentFunctionalWorkflow.run,
            "Tell me about San Francisco",
            id=f"functional-react-agent-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert "San Francisco" in result["answer"]
    assert result["steps"] == 2  # two tool calls
