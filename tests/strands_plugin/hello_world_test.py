import uuid

import pytest
from temporalio.client import Client
from temporalio.contrib.strands import StrandsPlugin
from temporalio.worker import Worker

from strands_plugin.hello_world.workflow import HelloWorldWorkflow
from tests.strands_plugin._mock_model import patch_bedrock


async def test_hello_world(client: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    patch_bedrock(monkeypatch, ["A haiku, for you."])

    task_queue = f"strands-hello-world-{uuid.uuid4()}"
    plugin = StrandsPlugin()

    config = client.config()
    config["plugins"] = [*config["plugins"], plugin]
    client = Client(**config)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[HelloWorldWorkflow],
        max_cached_workflows=0,
    ):
        result = await client.execute_workflow(
            HelloWorldWorkflow.run,
            "Write a haiku.",
            id=f"strands-hello-world-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert result == "A haiku, for you.\n"
