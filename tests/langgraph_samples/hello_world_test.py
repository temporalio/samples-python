"""Tests for the hello_world LangGraph sample."""

import uuid

import pytest
from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.contrib.langgraph._graph_registry import get_global_registry
from temporalio.worker import Worker

from langgraph_samples.hello_world.graph import build_hello_graph
from langgraph_samples.hello_world.workflow import HelloWorldWorkflow


@pytest.fixture(autouse=True)
def clear_registry() -> None:
    """Clear the global graph registry before each test."""
    get_global_registry().clear()


async def test_hello_world_workflow(client: Client) -> None:
    """Test that the hello world workflow processes a query correctly."""
    task_queue = f"hello-world-test-{uuid.uuid4()}"

    # Create plugin with the graph
    plugin = LangGraphPlugin(graphs={"hello_graph": build_hello_graph})

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[HelloWorldWorkflow],
        plugins=[plugin],
    ):
        result = await client.execute_workflow(
            HelloWorldWorkflow.run,
            "Hello from test",
            id=f"hello-world-{uuid.uuid4()}",
            task_queue=task_queue,
        )

        assert result["result"] == "Processed: Hello from test"


async def test_hello_world_empty_query(client: Client) -> None:
    """Test hello world workflow with empty query."""
    task_queue = f"hello-world-test-{uuid.uuid4()}"

    plugin = LangGraphPlugin(graphs={"hello_graph": build_hello_graph})

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[HelloWorldWorkflow],
        plugins=[plugin],
    ):
        result = await client.execute_workflow(
            HelloWorldWorkflow.run,
            "",
            id=f"hello-world-{uuid.uuid4()}",
            task_queue=task_queue,
        )

        assert result["result"] == "Processed: "
