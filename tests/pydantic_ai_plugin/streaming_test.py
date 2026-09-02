import uuid
from datetime import timedelta

from pydantic_ai.run import AgentRunResultEvent
from temporalio.client import Client
from temporalio.worker import Worker

from pydantic_ai_plugin.streaming.workflow import (
    StreamingInput,
    StreamingWorkflow,
    durability,
)
from tests.pydantic_ai_plugin.helpers import with_pydantic_ai


async def test_stream_ends_with_agent_result(client: Client) -> None:
    client = with_pydantic_ai(client)
    task_queue = f"pydantic-ai-streaming-{uuid.uuid4()}"
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[StreamingWorkflow],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            StreamingWorkflow.run,
            StreamingInput(prompt="Stream a response."),
            id=f"pydantic-ai-streaming-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        stream = durability.stream_agent_events(
            client,
            handle,
            output_type=str,
            poll_cooldown=timedelta(milliseconds=10),
        )
        events = [event async for event in stream]
        result = await handle.result()

    assert result == "The durable response is complete."
    assert isinstance(events[-1], AgentRunResultEvent)
    assert stream.result is not None
    assert stream.result.output == result


async def test_streaming_workflow_finishes_without_subscriber(client: Client) -> None:
    client = with_pydantic_ai(client)
    task_queue = f"pydantic-ai-streaming-unwatched-{uuid.uuid4()}"
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[StreamingWorkflow],
        max_cached_workflows=0,
    ):
        result = await client.execute_workflow(
            StreamingWorkflow.run,
            StreamingInput(
                prompt="Run unwatched.",
                drain_timeout_seconds=0.01,
            ),
            id=f"pydantic-ai-streaming-unwatched-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert result == "The durable response is complete."
