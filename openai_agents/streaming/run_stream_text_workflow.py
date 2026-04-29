from __future__ import annotations

import asyncio
import uuid

from agents.items import TResponseStreamEvent
from openai.types.responses import ResponseTextDeltaEvent
from temporalio.api.common.v1 import Payload
from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin
from temporalio.contrib.workflow_stream import WorkflowStreamClient

from openai_agents.streaming.shared import (
    TASK_QUEUE,
    TOPIC_DONE,
    TOPIC_EVENTS,
    race_with_workflow,
)
from openai_agents.streaming.workflows.stream_text_workflow import (
    StreamTextInput,
    StreamTextWorkflow,
)


async def main() -> None:
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

    stream = WorkflowStreamClient.create(client, workflow_id)
    converter = client.data_converter.payload_converter

    async def render() -> None:
        # Subscribe to both the streaming-event topic and the workflow's
        # done-sentinel so we can break cleanly without racing
        # handle.result() against the next poll. result_type is left
        # unset (we get raw Payloads) because the two topics carry
        # different types — we decode based on item.topic.
        async for item in stream.subscribe([TOPIC_EVENTS, TOPIC_DONE]):
            if item.topic == TOPIC_DONE:
                return
            assert isinstance(item.data, Payload)
            event = converter.from_payload(item.data, TResponseStreamEvent)
            if event.type == "raw_response_event" and isinstance(
                event.data, ResponseTextDeltaEvent
            ):
                print(event.data.delta, end="", flush=True)

    result = await race_with_workflow(render(), handle)
    print("\n--- final result ---")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
