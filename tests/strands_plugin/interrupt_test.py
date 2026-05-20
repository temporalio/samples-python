import uuid

import pytest
from temporalio.client import Client
from temporalio.contrib.strands import StrandsPlugin
from temporalio.worker import Worker

from strands_plugin.interrupt.workflow import InterruptWorkflow, delete_thing
from tests.strands_plugin._mock_model import patch_bedrock


async def test_interrupt(client: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    patch_bedrock(
        monkeypatch,
        [
            {"name": "delete_thing", "input": {"name": "system"}},
            {"name": "delete_thing", "input": {"name": "system"}},
            "Done!",
        ],
    )

    task_queue = f"strands-interrupt-{uuid.uuid4()}"
    plugin = StrandsPlugin()

    config = client.config()
    config["plugins"] = [*config["plugins"], plugin]
    client = Client(**config)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[InterruptWorkflow],
        activities=[delete_thing],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            InterruptWorkflow.run,
            "Delete the system user.",
            id=f"strands-interrupt-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        await handle.signal(InterruptWorkflow.approve, "approve")
        result = await handle.result()

    assert result == "Done!\n"
