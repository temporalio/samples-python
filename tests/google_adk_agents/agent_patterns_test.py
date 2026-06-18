import uuid

import pytest
from temporalio.client import Client
from temporalio.contrib.google_adk_agents import GoogleAdkPlugin
from temporalio.worker import Worker

from google_adk_agents.agent_patterns.workflows.multi_agent_workflow import (
    MultiAgentWorkflow,
)
from tests.google_adk_agents._mock_model import patch_model, text, tool_call


async def test_agent_patterns(client: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    patch_model(
        monkeypatch,
        [
            tool_call("transfer_to_agent", {"agent_name": "researcher"}),
            tool_call("transfer_to_agent", {"agent_name": "writer"}),
            text("snow on the mountain"),
        ],
    )

    task_queue = f"google-adk-agents-agent-patterns-{uuid.uuid4()}"
    plugin = GoogleAdkPlugin()

    config = client.config()
    config["plugins"] = [*config["plugins"], plugin]
    client = Client(**config)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[MultiAgentWorkflow],
        max_cached_workflows=0,
    ):
        result = await client.execute_workflow(
            MultiAgentWorkflow.run,
            "mountains",
            id=f"google-adk-agents-agent-patterns-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert result == "snow on the mountain"
