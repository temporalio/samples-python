import uuid

import pytest
from temporalio.client import Client
from temporalio.contrib.strands import StrandsPlugin
from temporalio.worker import Worker

from strands_plugin.hooks.workflow import HooksWorkflow, persist_tool_call
from tests.strands_plugin._mock_model import patch_bedrock


async def test_hooks(client: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    patch_bedrock(
        monkeypatch,
        [
            {"name": "echo", "input": {"text": "hi"}},
            "Done!",
        ],
    )

    task_queue = f"strands-hooks-{uuid.uuid4()}"
    plugin = StrandsPlugin()

    config = client.config()
    config["plugins"] = [*config["plugins"], plugin]
    client = Client(**config)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[HooksWorkflow],
        activities=[persist_tool_call],
        max_cached_workflows=0,
    ):
        fired = await client.execute_workflow(
            HooksWorkflow.run,
            "Echo hi.",
            id=f"strands-hooks-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert fired == ["echo"]
