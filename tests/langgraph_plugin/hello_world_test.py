import uuid
from datetime import timedelta

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.worker import Worker

from langgraph_plugin.graph_api.hello_world.workflow import (
    HelloWorldWorkflow,
    hello_graph,
)


async def test_hello_world_graph_api(client: Client) -> None:
    task_queue = f"hello-world-test-{uuid.uuid4()}"
    plugin = LangGraphPlugin(graphs=[hello_graph])

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[HelloWorldWorkflow],
        plugins=[plugin],
    ):
        result = await client.execute_workflow(
            HelloWorldWorkflow.run,
            "test query",
            id=f"hello-world-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert result == "Processed: test query"


async def test_hello_world_empty_string(client: Client) -> None:
    task_queue = f"hello-world-empty-test-{uuid.uuid4()}"
    plugin = LangGraphPlugin(graphs=[hello_graph])

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[HelloWorldWorkflow],
        plugins=[plugin],
    ):
        result = await client.execute_workflow(
            HelloWorldWorkflow.run,
            "",
            id=f"hello-world-empty-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert result == "Processed: "
