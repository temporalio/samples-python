import uuid
from datetime import timedelta
from typing import Any, cast

from agents.items import TResponseStreamEvent
from openai.types.responses import ResponseCompletedEvent, ResponseTextDeltaEvent
from temporalio.client import Client
from temporalio.common import RawValue
from temporalio.contrib.openai_agents import ModelActivityParameters, OpenAIAgentsPlugin
from temporalio.contrib.workflow_streams import WorkflowStreamClient
from temporalio.worker import Worker

from openai_agents.streaming.activities.joke_activities import how_many_jokes
from openai_agents.streaming.shared import (
    TOPIC_DONE,
    TOPIC_EVENTS,
    TOPIC_ITEMS,
    ItemEvent,
)
from openai_agents.streaming.workflows.stream_items_workflow import (
    StreamItemsInput,
    StreamItemsWorkflow,
)
from openai_agents.streaming.workflows.stream_text_workflow import (
    StreamTextInput,
    StreamTextWorkflow,
)
from tests.openai_agents._mock_model import (
    FailMidStream,
    ScriptedModelProvider,
    ScriptEntry,
    ToolCall,
)

JOKES = (
    "Why did the developer go broke? He used up all his cache. "
    "Why do programmers prefer dark mode? Light attracts bugs."
)

# TResponseStreamEvent is a typing.Annotated union rather than a class, so it
# needs a cast to satisfy from_payload's type[T] signature.
EVENT_TYPE = cast(type, TResponseStreamEvent)

# Fast polling so a test does not spend most of its time waiting on cooldowns.
POLL_COOLDOWN = timedelta(milliseconds=50)


def _client_with_plugin(client: Client, script: list[ScriptEntry]) -> Client:
    config = client.config()
    config["plugins"] = [
        *config["plugins"],
        OpenAIAgentsPlugin(
            model_params=ModelActivityParameters(
                start_to_close_timeout=timedelta(seconds=30),
                heartbeat_timeout=timedelta(seconds=10),
                streaming_topic=TOPIC_EVENTS,
            ),
            model_provider=ScriptedModelProvider(script),
        ),
    ]
    return Client(**config)


async def test_stream_text(client: Client) -> None:
    client = _client_with_plugin(client, [JOKES])
    task_queue = f"openai-agents-stream-text-{uuid.uuid4()}"
    workflow_id = f"stream-text-{uuid.uuid4()}"

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[StreamTextWorkflow],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            StreamTextWorkflow.run,
            StreamTextInput(prompt="Please tell me 2 jokes."),
            id=workflow_id,
            task_queue=task_queue,
        )

        # Same shape as run_stream_text_workflow.py: one iterator over both
        # topics, RawValue payloads decoded per item.topic, break on the
        # terminator the workflow publishes.
        stream = WorkflowStreamClient.create(client, workflow_id)
        converter = client.data_converter.payload_converter
        deltas: list[str] = []
        saw_terminator = False
        async for item in stream.subscribe(
            [TOPIC_EVENTS, TOPIC_DONE],
            result_type=RawValue,
            poll_cooldown=POLL_COOLDOWN,
        ):
            if item.topic == TOPIC_DONE:
                saw_terminator = True
                break
            event: Any = converter.from_payload(item.data.payload, EVENT_TYPE)
            if isinstance(event, ResponseTextDeltaEvent):
                deltas.append(event.delta)

        result = await handle.result()

    assert saw_terminator, "subscriber exited without seeing the terminator"
    # Subscribers see native OpenAI events, so the deltas arrive unwrapped and
    # reassemble into exactly what the workflow returns.
    assert len(deltas) > 1, "expected the text to arrive as several deltas"
    assert "".join(deltas) == JOKES
    assert result == JOKES


async def test_retried_attempt_is_detectable(client: Client) -> None:
    """A retried model activity re-streams, and subscribers can tell.

    Turn one calls the tool; turn two dies after four deltas and its retry
    answers in full. The partial deltas are already on the stream when the
    attempt fails, so a subscriber that just concatenates them renders the
    truncated text followed by the whole answer. run_stream_text_workflow.py
    finds the seam with the rule asserted here: a sequence_number that fails
    to advance while a response is still in flight. Turn two's own restart
    must not trip it — that one follows a completed response.
    """
    client = _client_with_plugin(
        client,
        [ToolCall("how_many_jokes"), FailMidStream(JOKES, after_deltas=4), JOKES],
    )
    task_queue = f"openai-agents-stream-retry-{uuid.uuid4()}"
    workflow_id = f"stream-retry-{uuid.uuid4()}"

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[StreamItemsWorkflow],
        activities=[how_many_jokes],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            StreamItemsWorkflow.run,
            StreamItemsInput(),
            id=workflow_id,
            task_queue=task_queue,
        )

        stream = WorkflowStreamClient.create(client, workflow_id)
        converter = client.data_converter.payload_converter
        all_deltas: list[str] = []
        deltas_since_restart: list[str] = []
        restarts = 0
        last_sequence = -1
        response_in_flight = False
        async for item in stream.subscribe(
            [TOPIC_EVENTS, TOPIC_DONE],
            result_type=RawValue,
            poll_cooldown=POLL_COOLDOWN,
        ):
            if item.topic == TOPIC_DONE:
                break
            event: Any = converter.from_payload(item.data.payload, EVENT_TYPE)

            sequence = event.sequence_number
            if sequence <= last_sequence and response_in_flight:
                restarts += 1
                deltas_since_restart = []
            last_sequence = sequence
            response_in_flight = not isinstance(event, ResponseCompletedEvent)

            if isinstance(event, ResponseTextDeltaEvent):
                all_deltas.append(event.delta)
                deltas_since_restart.append(event.delta)

        result = await handle.result()

    assert restarts == 1, "expected exactly one detected retry"
    # The failed attempt's partial text is on the stream ahead of the retry's,
    # so a naive reassembly is corrupt while the workflow's result is not.
    naive = "".join(all_deltas)
    assert len(naive) > len(JOKES) and naive.endswith(JOKES)
    # Discarding at the seam recovers exactly the successful attempt.
    assert "".join(deltas_since_restart) == JOKES
    assert result == JOKES


async def test_stream_items(client: Client) -> None:
    # Turn one calls the tool, turn two answers with the jokes.
    client = _client_with_plugin(client, [ToolCall("how_many_jokes"), JOKES])
    task_queue = f"openai-agents-stream-items-{uuid.uuid4()}"
    workflow_id = f"stream-items-{uuid.uuid4()}"

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[StreamItemsWorkflow],
        activities=[how_many_jokes],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            StreamItemsWorkflow.run,
            StreamItemsInput(),
            id=workflow_id,
            task_queue=task_queue,
        )

        stream = WorkflowStreamClient.create(client, workflow_id)
        converter = client.data_converter.payload_converter
        events: list[ItemEvent] = []
        saw_terminator = False
        async for item in stream.subscribe(
            [TOPIC_ITEMS, TOPIC_DONE],
            result_type=RawValue,
            poll_cooldown=POLL_COOLDOWN,
        ):
            if item.topic == TOPIC_DONE:
                saw_terminator = True
                break
            events.append(converter.from_payload(item.data.payload, ItemEvent))

        result = await handle.result()

    assert saw_terminator, "subscriber exited without seeing the terminator"
    assert [e.kind for e in events] == [
        "agent_updated",
        "tool_call",
        "tool_output",
        "message_output",
    ]
    assert events[0].detail == "Joker"
    assert events[1].detail == "how_many_jokes"
    assert 1 <= int(events[2].detail) <= 10
    assert events[3].detail == JOKES
    assert result == JOKES
