import uuid
from datetime import timedelta

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.worker import Worker

from langgraph_plugin.functional_api.hello_world.workflow import (
    HelloWorldFunctionalWorkflow,
    activity_options,
    all_tasks,
    hello_entrypoint,
)


async def test_functional_hello_world(client: Client) -> None:
    task_queue = f"functional-hello-test-{uuid.uuid4()}"
    plugin = LangGraphPlugin(
        entrypoints={"hello-world": hello_entrypoint},
        tasks=all_tasks,
        activity_options=activity_options,
    )

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[HelloWorldFunctionalWorkflow],
        plugins=[plugin],
    ):
        result = await client.execute_workflow(
            HelloWorldFunctionalWorkflow.run,
            "test query",
            id=f"functional-hello-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert result == {"result": "Processed: test query"}
