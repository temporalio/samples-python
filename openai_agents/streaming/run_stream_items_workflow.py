"""Start StreamItemsWorkflow and render its run as a play-by-play."""

from __future__ import annotations

import asyncio
import uuid

from temporalio.client import Client
from temporalio.common import RawValue
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin
from temporalio.contrib.workflow_streams import WorkflowStreamClient

from openai_agents.streaming.shared import (
    TASK_QUEUE,
    TOPIC_DONE,
    TOPIC_ITEMS,
    ItemEvent,
)
from openai_agents.streaming.workflows.stream_items_workflow import (
    StreamItemsInput,
    StreamItemsWorkflow,
)


async def main() -> None:
    client = await Client.connect(
        "localhost:7233",
        plugins=[OpenAIAgentsPlugin()],
    )

    workflow_id = f"stream-items-{uuid.uuid4().hex[:8]}"
    handle = await client.start_workflow(
        StreamItemsWorkflow.run,
        StreamItemsInput(),
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )

    stream = WorkflowStreamClient.create(client, workflow_id)
    converter = client.data_converter.payload_converter

    print("=== Run starting ===")
    # result_type=RawValue so the two topics can be decoded per item.topic.
    # The raw model events the streaming activity publishes on TOPIC_EVENTS are
    # on the stream too; this subscriber just isn't interested in them.
    async for item in stream.subscribe([TOPIC_ITEMS, TOPIC_DONE], result_type=RawValue):
        if item.topic == TOPIC_DONE:
            break
        event = converter.from_payload(item.data.payload, ItemEvent)
        if event.kind == "agent_updated":
            print(f"Agent updated: {event.detail}")
        elif event.kind == "tool_call":
            print(f"-- Tool was called: {event.detail}")
        elif event.kind == "tool_output":
            print(f"-- Tool output: {event.detail}")
        elif event.kind == "message_output":
            print(f"-- Message output:\n {event.detail}")

    result = await handle.result()
    print("=== Run complete ===")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
