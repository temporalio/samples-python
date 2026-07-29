import uuid

import pytest
from temporalio.client import Client
from temporalio.contrib.google_adk_agents import (
    GoogleAdkPlugin,
    TemporalMcpToolSetProvider,
)
from temporalio.worker import Worker

from google_adk_agents.mcp.toolsets import echo_toolset
from google_adk_agents.mcp.workflows.echo_workflow import EchoMcpWorkflow
from tests.google_adk_agents._mock_model import patch_model, text, tool_call


async def test_mcp(client: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    patch_model(
        monkeypatch,
        [
            tool_call("echo", {"message": "hello from MCP"}),
            text("Done!"),
        ],
    )

    task_queue = f"google-adk-agents-mcp-{uuid.uuid4()}"
    plugin = GoogleAdkPlugin(
        toolset_providers=[TemporalMcpToolSetProvider("echo", echo_toolset)]
    )

    config = client.config()
    config["plugins"] = [*config["plugins"], plugin]
    client = Client(**config)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[EchoMcpWorkflow],
        max_cached_workflows=0,
    ):
        result = await client.execute_workflow(
            EchoMcpWorkflow.run,
            "Echo 'hello from MCP'.",
            id=f"google-adk-agents-mcp-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert result == "Done!"
