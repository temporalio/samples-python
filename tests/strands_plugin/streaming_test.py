import asyncio
import uuid
from datetime import timedelta

import pytest
from strands.types.streaming import StreamEvent
from temporalio.client import Client
from temporalio.contrib.strands import StrandsPlugin
from temporalio.contrib.workflow_streams import WorkflowStreamClient
from temporalio.worker import Worker

from strands_plugin.streaming.workflow import StreamingWorkflow
from tests.strands_plugin._mock_model import patch_bedrock


async def test_streaming(client: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    patch_bedrock(monkeypatch, ["Done!"])

    task_queue = f"strands-streaming-{uuid.uuid4()}"
    plugin = StrandsPlugin()
    workflow_id = f"strands-streaming-{uuid.uuid4()}"

    config = client.config()
    config["plugins"] = [*config["plugins"], plugin]
    client = Client(**config)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[StreamingWorkflow],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            StreamingWorkflow.run,
            "Hello",
            id=workflow_id,
            task_queue=task_queue,
        )

        stream = WorkflowStreamClient.create(client, workflow_id)
        events: list[StreamEvent] = []

        async def collect() -> None:
            async for item in stream.subscribe(
                ["events"],
                from_offset=0,
                result_type=StreamEvent,
                poll_cooldown=timedelta(milliseconds=50),
            ):
                events.append(item.data)
                if len(events) >= 4:
                    return

        collect_task = asyncio.create_task(collect())
        assert await handle.result() == "Done!\n"
        await asyncio.wait_for(collect_task, timeout=10.0)

    assert any("messageStart" in e for e in events)
    assert any("messageStop" in e for e in events)
