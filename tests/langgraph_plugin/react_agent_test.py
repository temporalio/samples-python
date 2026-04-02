"""Tests for the react_agent LangGraph sample."""

import uuid

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.worker import Worker

from langgraph_plugin.graph_api.react_agent.graph import build_react_agent
from langgraph_plugin.graph_api.react_agent.workflow import ReActAgentWorkflow

from .conftest import requires_openai


@requires_openai
async def test_react_agent_workflow(client: Client) -> None:
    """Test ReAct agent workflow with a simple query.

    This test requires OPENAI_API_KEY to be set.
    """
    task_queue = f"react-agent-test-{uuid.uuid4()}"

    plugin = LangGraphPlugin(graphs={"react_agent": build_react_agent})

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[ReActAgentWorkflow],
        plugins=[plugin],
    ):
        result = await client.execute_workflow(
            ReActAgentWorkflow.run,
            "What is 2 + 2?",
            id=f"react-agent-{uuid.uuid4()}",
            task_queue=task_queue,
        )

        # The result should contain messages with the answer
        assert "messages" in result
        assert len(result["messages"]) > 0


@requires_openai
async def test_react_agent_with_tools(client: Client) -> None:
    """Test ReAct agent using tools.

    This test requires OPENAI_API_KEY to be set.
    """
    task_queue = f"react-agent-test-{uuid.uuid4()}"

    plugin = LangGraphPlugin(graphs={"react_agent": build_react_agent})

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[ReActAgentWorkflow],
        plugins=[plugin],
    ):
        # Query that should use the get_weather tool
        result = await client.execute_workflow(
            ReActAgentWorkflow.run,
            "What's the weather in New York?",
            id=f"react-agent-{uuid.uuid4()}",
            task_queue=task_queue,
        )

        assert "messages" in result
        # Should have used the weather tool and returned a result
        messages = result["messages"]
        assert len(messages) > 1  # At least user message and AI response
