import uuid

import pytest
from temporalio.client import Client
from temporalio.contrib.strands import StrandsPlugin
from temporalio.worker import Worker

from strands_plugin.mcp.run_worker import _make_echo_client
from strands_plugin.mcp.workflow import MCPWorkflow
from tests.strands_plugin._mock_model import patch_bedrock


async def test_mcp(client: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    patch_bedrock(
        monkeypatch,
        [
            {"name": "echo", "input": {"message": "hello from MCP"}},
            "Done!",
        ],
    )

    task_queue = f"strands-mcp-{uuid.uuid4()}"
    plugin = StrandsPlugin(mcp_clients={"echo": _make_echo_client})

    config = client.config()
    config["plugins"] = [*config["plugins"], plugin]
    client = Client(**config)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[MCPWorkflow],
        max_cached_workflows=0,
    ):
        result = await client.execute_workflow(
            MCPWorkflow.run,
            "Echo hello from MCP.",
            id=f"strands-mcp-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert result == "Done!\n"
