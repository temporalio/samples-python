"""Tests for the hello_world Functional API sample."""

import uuid

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphFunctionalPlugin
from temporalio.worker import Worker

from langgraph_plugin.functional_api.hello_world.entrypoint import (
    hello_world_entrypoint,
)
from langgraph_plugin.functional_api.hello_world.workflow import HelloWorldWorkflow


async def test_hello_world_functional_workflow(client: Client) -> None:
    """Test that the hello world functional workflow processes a query correctly."""
    task_queue = f"hello-world-functional-test-{uuid.uuid4()}"

    plugin = LangGraphFunctionalPlugin(
        entrypoints={"hello_world_entrypoint": hello_world_entrypoint},
    )

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[HelloWorldWorkflow],
        plugins=[plugin],
    ):
        result = await client.execute_workflow(
            HelloWorldWorkflow.run,
            "Hello from test",
            id=f"hello-world-functional-{uuid.uuid4()}",
            task_queue=task_queue,
        )

        assert result["query"] == "Hello from test"
        assert result["result"] == "Processed: Hello from test"


async def test_hello_world_functional_empty_query(client: Client) -> None:
    """Test hello world functional workflow with empty query."""
    task_queue = f"hello-world-functional-test-{uuid.uuid4()}"

    plugin = LangGraphFunctionalPlugin(
        entrypoints={"hello_world_entrypoint": hello_world_entrypoint},
    )

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[HelloWorldWorkflow],
        plugins=[plugin],
    ):
        result = await client.execute_workflow(
            HelloWorldWorkflow.run,
            "",
            id=f"hello-world-functional-{uuid.uuid4()}",
            task_queue=task_queue,
        )

        assert result["query"] == ""
        assert result["result"] == "Processed: "
