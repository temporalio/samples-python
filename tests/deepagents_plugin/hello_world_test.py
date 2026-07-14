import uuid

from temporalio.client import Client
from temporalio.contrib.deepagents import DeepAgentsPlugin
from temporalio.contrib.deepagents.testing import mock_model_provider
from temporalio.worker import Worker

from deepagents_plugin.hello_world.workflow import HelloWorldAgent


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
        result = await client.execute_workflow(
            HelloWorldAgent.run,
            "What is Temporal?",
            id=f"deepagents-hello-world-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert "durable" in result
