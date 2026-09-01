"""Start StreamTextWorkflow and render its model output as it streams.

Delivery is at-least-once per model-activity attempt: an attempt that fails
mid-response leaves its partial deltas on the stream, and the retry publishes
a whole new response. Unlike ``workflow_streams/activities/llm_activity.py``,
which publishes an explicit ``RetryEvent`` on ``activity.info().attempt > 1``,
the plugin's streaming activity emits no retry marker — so this subscriber
infers a new attempt from the stream itself and says so, rather than silently
running the two responses together. (``workflow_streams/run_llm.py`` goes a
step further and erases the failed attempt's output with ANSI escapes.)
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, cast

from agents.items import TResponseStreamEvent
from openai.types.responses import ResponseCompletedEvent, ResponseTextDeltaEvent
from temporalio.client import Client
from temporalio.common import RawValue
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin
from temporalio.contrib.workflow_streams import WorkflowStreamClient

from openai_agents.streaming.shared import TASK_QUEUE, TOPIC_DONE, TOPIC_EVENTS
from openai_agents.streaming.workflows.stream_text_workflow import (
    StreamTextInput,
    StreamTextWorkflow,
)

# TResponseStreamEvent is a typing.Annotated union rather than a class, so it
# needs a cast to satisfy from_payload's type[T] signature. The plugin's
# pydantic converter resolves the union's discriminator at runtime.
EVENT_TYPE = cast(type, TResponseStreamEvent)


async def main() -> None:
    # The plugin's data converter is what decodes the OpenAI event payloads
    # published on TOPIC_EVENTS.
    client = await Client.connect(
        "localhost:7233",
        plugins=[OpenAIAgentsPlugin()],
    )

    workflow_id = f"stream-text-{uuid.uuid4().hex[:8]}"
    handle = await client.start_workflow(
        StreamTextWorkflow.run,
        StreamTextInput(prompt="Please tell me 5 jokes."),
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )

    # @@@SNIPSTART python-openai-agents-streaming-client
    stream = WorkflowStreamClient.create(client, workflow_id)
    converter = client.data_converter.payload_converter

    # A single iterator over both topics — one subscriber, no cancellation race
    # between concurrent ones. result_type=RawValue delivers the underlying
    # Payload so heterogeneous topics can be decoded per item.topic. The loop
    # ends on the in-band terminator, or by the iterator exhausting if the
    # workflow reaches a terminal state without publishing one (e.g. on
    # failure); either way handle.result() below surfaces the outcome.
    last_sequence = -1
    response_in_flight = False
    async for item in stream.subscribe(
        [TOPIC_EVENTS, TOPIC_DONE], result_type=RawValue
    ):
        if item.topic == TOPIC_DONE:
            break
        # Subscribers receive native OpenAI events, not the agents-SDK
        # StreamEvent wrappers that stream_events() yields in the workflow.
        event: Any = converter.from_payload(item.data.payload, EVENT_TYPE)

        # Every event carries a sequence_number that starts at 0 per response,
        # so a number that does not advance means a new response is streaming.
        # That is a retry only if the previous one never completed: each turn
        # of a multi-turn run is its own response and restarts the count too.
        # The retry is an independently sampled answer rather than a
        # continuation, so mark the seam instead of letting the failed
        # attempt's partial text run into the new one. The workflow's return
        # value is unaffected — stream_events() there sees only the attempt
        # that succeeded.
        sequence = event.sequence_number
        if sequence <= last_sequence and response_in_flight:
            print("\n\n[model activity retried — output restarts here]\n")
        last_sequence = sequence
        response_in_flight = not isinstance(event, ResponseCompletedEvent)

        if isinstance(event, ResponseTextDeltaEvent):
            print(event.delta, end="", flush=True)
    # @@@SNIPEND

    result = await handle.result()
    print("\n--- final result ---")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
