import uuid

from temporalio.client import Client
from temporalio.contrib.deepagents import DeepAgentsPlugin
from temporalio.contrib.deepagents.testing import mock_model_provider
from temporalio.worker import Worker

from deepagents_plugin.hello_world.workflow import HelloWorldAgent
from tests.deepagents_plugin.helpers import INVOKE_MODEL, count_scheduled_activities


async def test_hello_world(client: Client) -> None:
    # A scripted model so the test runs offline (no ANTHROPIC_API_KEY needed).
    plugin = DeepAgentsPlugin(
        model_provider=mock_model_provider(
            ["Temporal is a durable execution platform."]
        ),
    )
    task_queue = f"deepagents-hello-world-{uuid.uuid4()}"

    config = client.config()
    config["plugins"] = [*config["plugins"], plugin]
    client = Client(**config)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[HelloWorldAgent],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            HelloWorldAgent.run,
            "What is Temporal?",
            id=f"deepagents-hello-world-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        result = await handle.result()

    assert "durable" in result
    # The model call really ran as a `deepagents.invoke_model` activity — the
    # durability the plugin exists to provide, which a content-only assertion
    # cannot distinguish from an in-workflow call.
    counts = await count_scheduled_activities(handle)
    assert counts[INVOKE_MODEL] >= 1, counts
