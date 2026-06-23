import asyncio
import uuid
from datetime import timedelta

import pytest
from google.adk.models.llm_response import LlmResponse
from temporalio.client import Client
from temporalio.contrib.google_adk_agents import GoogleAdkPlugin
from temporalio.contrib.workflow_streams import WorkflowStreamClient
from temporalio.worker import Worker

from google_adk_agents.streaming.workflows.streaming_workflow import (
    StreamingAgentWorkflow,
)
from tests.google_adk_agents._mock_model import patch_model, text


async def test_streaming(client: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    patch_model(
        monkeypatch,
        [text("Once "), text("upon a robot.")],
        stream_chunks=True,
    )

    task_queue = f"google-adk-agents-streaming-{uuid.uuid4()}"
    plugin = GoogleAdkPlugin()
    workflow_id = f"google-adk-agents-streaming-{uuid.uuid4()}"

    config = client.config()
    config["plugins"] = [*config["plugins"], plugin]
    client = Client(**config)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[StreamingAgentWorkflow],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            StreamingAgentWorkflow.run,
            "Tell me a story",
            id=workflow_id,
            task_queue=task_queue,
        )

        stream = WorkflowStreamClient.create(client, workflow_id)
        chunks: list[str] = []

        async def collect() -> None:
            async for item in stream.subscribe(
                ["responses"],
                from_offset=0,
                result_type=LlmResponse,
                poll_cooldown=timedelta(milliseconds=50),
            ):
                response = item.data
                if response.content and response.content.parts:
                    for part in response.content.parts:
                        if part.text:
                            chunks.append(part.text)
                if len(chunks) >= 2:
                    return

        collect_task = asyncio.create_task(collect())
        assert await handle.result() == "upon a robot."
        await asyncio.wait_for(collect_task, timeout=10.0)

    assert chunks == ["Once ", "upon a robot."]
