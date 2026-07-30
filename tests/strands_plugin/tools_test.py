import uuid

import pytest
from temporalio.client import Client
from temporalio.contrib.strands import StrandsPlugin
from temporalio.worker import Worker

from strands_plugin.tools.workflow import (
    ToolsWorkflow,
    environment_activity,
    fetch_weather,
)
from tests.strands_plugin._mock_model import patch_bedrock


async def test_tools(client: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    patch_bedrock(
        monkeypatch,
        [
            {
                "name": "letter_counter",
                "input": {"word": "strawberry", "letter": "R"},
            },
            {"name": "fetch_weather", "input": {"city": "San Francisco"}},
            {"name": "environment", "input": {"action": "validate", "name": "PATH"}},
            "Done!",
        ],
    )

    task_queue = f"strands-tools-{uuid.uuid4()}"
    plugin = StrandsPlugin()

    config = client.config()
    config["plugins"] = [*config["plugins"], plugin]
    client = Client(**config)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[ToolsWorkflow],
        activities=[fetch_weather, environment_activity],
        max_cached_workflows=0,
    ):
        result = await client.execute_workflow(
            ToolsWorkflow.run,
            "Use all three tools.",
            id=f"strands-tools-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert result == "Done!\n"
