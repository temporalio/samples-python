import asyncio
import uuid
from datetime import timedelta

from langchain_core.load import load
from temporalio.client import Client
from temporalio.contrib.deepagents import DeepAgentsPlugin
from temporalio.contrib.deepagents.testing import mock_model_provider
from temporalio.contrib.workflow_streams import WorkflowStreamClient
from temporalio.worker import Worker

from deepagents_plugin.streaming.workflow import STREAMING_TOPIC, StreamingWorkflow
from tests.deepagents_plugin.helpers import (
    INVOKE_MODEL,
    INVOKE_MODEL_STREAMING,
    count_scheduled_activities,
)


async def test_streaming(client: Client) -> None:
    # streaming_topic=... flips model dispatch to the streaming activity, which
    # publishes chunks to the topic while still returning the aggregated message
    # as the durable result. An in-test subscriber collects the chunks.
    expected = "Streamed answer."
    plugin = DeepAgentsPlugin(
        model_provider=mock_model_provider([expected]),
        streaming_topic=STREAMING_TOPIC,
    )
    task_queue = f"deepagents-streaming-{uuid.uuid4()}"

    config = client.config()
    config["plugins"] = [*config["plugins"], plugin]
    client = Client(**config)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[StreamingWorkflow],
        max_cached_workflows=0,
    ):
        workflow_id = f"deepagents-streaming-{uuid.uuid4()}"
        handle = await client.start_workflow(
            StreamingWorkflow.run,
            "Write a sentence about durable execution.",
            id=workflow_id,
            task_queue=task_queue,
        )

        chunks: list[str] = []

        async def consume() -> None:
            stream = WorkflowStreamClient.create(client, workflow_id)
            async for item in stream.subscribe(
                [STREAMING_TOPIC],
                from_offset=0,
                result_type=dict,
                poll_cooldown=timedelta(milliseconds=10),
            ):
                text = getattr(load(item.data), "content", "")
                if text:
                    chunks.append(text)
                # The subscription is open-ended; return once the full answer
                # has been observed.
                if expected in "".join(chunks):
                    return

        consume_task = asyncio.create_task(consume())
        result = await handle.result()
        # No fixed sleep: the subscriber exits as soon as it has seen the
        # streamed content; the timeout only bounds a regression.
        await asyncio.wait_for(consume_task, timeout=10.0)

    # The durable result matches the non-streaming path...
    assert expected in result
    # ...and the same content was streamed out to the subscriber.
    assert chunks, "expected at least one streamed chunk"
    assert expected in "".join(chunks)
    # Dispatch really flipped to the streaming activity: with streaming_topic
    # set, the model call ran as invoke_model_streaming, not invoke_model.
    counts = await count_scheduled_activities(handle)
    assert counts[INVOKE_MODEL_STREAMING] == 1, counts
    assert counts[INVOKE_MODEL] == 0, counts
