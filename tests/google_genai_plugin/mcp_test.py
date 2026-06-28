import sys
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from google import genai
from google.genai.types import HttpResponse as SdkHttpResponse
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from temporalio.client import Client
from temporalio.contrib.google_genai import GoogleGenAIPlugin
from temporalio.contrib.google_genai.testing import (
    function_call_response,
    text_response,
)
from temporalio.worker import Worker

from google_genai_plugin.mcp.workflow import McpWorkflow

ECHO_SERVER = str(
    Path(__file__).parents[2] / "google_genai_plugin" / "mcp" / "echo_mcp_server.py"
)


@asynccontextmanager
async def _echo_session() -> AsyncIterator[ClientSession]:
    params = StdioServerParameters(command=sys.executable, args=[ECHO_SERVER])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


def _mcp_plugin(responses: list[str]) -> GoogleGenAIPlugin:
    """A plugin with scripted model HTTP plus a real echo MCP server.

    Mirrors what ``GeminiTestServer.plugin()`` does for the model HTTP layer,
    but also registers an MCP server (which ``GeminiTestServer`` does not), so
    the MCP ``list_tools`` / ``call_tool`` activities run for real.
    """
    genai_client = genai.Client(api_key="fake-test-key")
    index = {"i": 0}

    async def fake_async_request(*_args: Any, **_kwargs: Any) -> SdkHttpResponse:
        body = responses[index["i"]]
        index["i"] += 1
        return SdkHttpResponse(headers={"content-type": "application/json"}, body=body)

    genai_client._api_client.async_request = fake_async_request  # type: ignore[assignment]
    return GoogleGenAIPlugin(genai_client, mcp_servers={"echo": _echo_session})


async def test_mcp(client: Client) -> None:
    plugin = _mcp_plugin(
        [
            function_call_response("echo", {"message": "durable execution"}),
            text_response("The echo tool returned: durable execution"),
        ]
    )

    config = client.config()
    config["plugins"] = [*config["plugins"], plugin]
    client = Client(**config)

    task_queue = f"google-genai-mcp-{uuid.uuid4()}"
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[McpWorkflow],
        max_cached_workflows=0,
    ):
        result = await client.execute_workflow(
            McpWorkflow.run,
            "Use the echo tool to echo back the phrase: durable execution.",
            id=f"google-genai-mcp-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert "durable execution" in result
