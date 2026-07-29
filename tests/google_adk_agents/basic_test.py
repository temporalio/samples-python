import uuid

import pytest
from temporalio.client import Client
from temporalio.contrib.google_adk_agents import GoogleAdkPlugin
from temporalio.worker import Worker

from google_adk_agents.basic.workflows.hello_world_workflow import (
    HelloWorldAgentWorkflow,
)
from tests.google_adk_agents._mock_model import patch_model, text


async def test_basic(client: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    patch_model(monkeypatch, [text("a quiet haiku")])

    task_queue = f"google-adk-agents-basic-{uuid.uuid4()}"
    plugin = GoogleAdkPlugin()

    config = client.config()
    config["plugins"] = [*config["plugins"], plugin]
    client = Client(**config)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[HelloWorldAgentWorkflow],
        max_cached_workflows=0,
    ):
        result = await client.execute_workflow(
            HelloWorldAgentWorkflow.run,
            "Say hi",
            id=f"google-adk-agents-basic-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert result == "a quiet haiku"
