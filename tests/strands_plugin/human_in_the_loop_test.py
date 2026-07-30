import uuid

import pytest
from temporalio.client import Client
from temporalio.contrib.strands import StrandsPlugin
from temporalio.worker import Worker

from strands_plugin.human_in_the_loop.workflow import HumanInTheLoopWorkflow
from tests.strands_plugin._mock_model import patch_bedrock


async def test_human_in_the_loop_approve(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    patch_bedrock(
        monkeypatch,
        [
            {"name": "delete_file", "input": {"path": "/tmp/sensitive.txt"}},
            "Done!",
        ],
    )

    task_queue = f"strands-hitl-{uuid.uuid4()}"
    plugin = StrandsPlugin()

    config = client.config()
    config["plugins"] = [*config["plugins"], plugin]
    client = Client(**config)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[HumanInTheLoopWorkflow],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            HumanInTheLoopWorkflow.run,
            "Delete /tmp/sensitive.txt",
            id=f"strands-hitl-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        await handle.signal(HumanInTheLoopWorkflow.approve, "approve")
        result = await handle.result()

    assert result == "Done!\n"
