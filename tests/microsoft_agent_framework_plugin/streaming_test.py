import asyncio
import uuid
from datetime import timedelta

from agent_framework import ChatResponseUpdate
from temporalio.client import Client
from temporalio.contrib.workflow_streams import WorkflowStreamClient
from temporalio.worker import Worker

from microsoft_agent_framework_plugin.streaming.workflow import (
    STREAMING_TOPIC,
    StreamingWorkflow,
)
from tests.microsoft_agent_framework_plugin._fake_chat_client import scripted_plugin
from tests.microsoft_agent_framework_plugin.helpers import (
    INVOKE_MODEL,
    INVOKE_MODEL_STREAMING,
    count_scheduled_activities,
    with_plugin,
)


async def test_streaming(client: Client) -> None:
    expected = "One. Two. Three. Four. Five. That is the whole count."
    plugin, _ = scripted_plugin([expected])
    client = with_plugin(client, plugin)
    task_queue = f"microsoft-agent-framework-streaming-{uuid.uuid4()}"
    workflow_id = f"microsoft-agent-framework-streaming-{uuid.uuid4()}"

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[StreamingWorkflow],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            StreamingWorkflow.run,
            "Count from 1 to 5.",
            id=workflow_id,
            task_queue=task_queue,
        )

        async def consume() -> list[str]:
            chunks: list[str] = []
            stream = WorkflowStreamClient.create(client, workflow_id)
            async for item in stream.subscribe(
                [STREAMING_TOPIC],
                from_offset=0,
                result_type=dict,
                poll_cooldown=timedelta(milliseconds=10),
            ):
                update = ChatResponseUpdate.from_dict(item.data)
                if update.text:
                    chunks.append(update.text)
            return chunks

        consume_task = asyncio.create_task(consume())
        result = await handle.result()
        # Once the Workflow is complete, subscribe reads the rest of the stream
        # and then ends.
        chunks = await consume_task
        # A subscriber that starts after the Workflow completed gets them all too.
        late_chunks = await consume()

    # The durable result is the whole text...
    assert result == expected
    # ...and the same text reached both subscribers in more than one update.
    assert len(chunks) > 1
    assert "".join(chunks) == expected
    assert late_chunks == chunks
    # The topic routed the call to the streaming Activity, not the plain one.
    counts = await count_scheduled_activities(handle)
    assert counts == {INVOKE_MODEL_STREAMING: 1}
    assert counts[INVOKE_MODEL] == 0
