import uuid

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.worker import Worker

from langgraph_plugin.graph_api.react_agent.workflow import (
    ReactAgentWorkflow,
    build_graph,
)


async def test_react_agent_graph_api(client: Client) -> None:
    task_queue = f"react-agent-test-{uuid.uuid4()}"
    plugin = LangGraphPlugin(graphs={"react-agent": build_graph()})

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[ReactAgentWorkflow],
        plugins=[plugin],
    ):
        result = await client.execute_workflow(
            ReactAgentWorkflow.run,
            "Tell me about San Francisco",
            id=f"react-agent-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert "San Francisco" in result
    assert "72" in result or "weather" in result.lower()
    assert "870,000" in result or "population" in result.lower()
