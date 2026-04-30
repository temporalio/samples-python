from __future__ import annotations

import asyncio
import uuid

from agents import ItemHelpers
from agents.items import TResponseStreamEvent
from temporalio.api.common.v1 import Payload
from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin
from temporalio.contrib.workflow_streams import WorkflowStreamClient

from openai_agents.streaming.shared import (
    TASK_QUEUE,
    TOPIC_DONE,
    TOPIC_EVENTS,
    race_with_workflow,
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

    async def render() -> None:
        print("=== Run starting ===")
        async for item in stream.subscribe([TOPIC_EVENTS, TOPIC_DONE]):
            if item.topic == TOPIC_DONE:
                return
            assert isinstance(item.data, Payload)
            event = converter.from_payload(item.data, TResponseStreamEvent)
            if event.type == "raw_response_event":
                continue
            if event.type == "agent_updated_stream_event":
                print(f"Agent updated: {event.new_agent.name}")
            elif event.type == "run_item_stream_event":
                if event.item.type == "tool_call_item":
                    name = getattr(event.item.raw_item, "name", "Unknown Tool")
                    print(f"-- Tool was called: {name}")
                elif event.item.type == "tool_call_output_item":
                    print(f"-- Tool output: {event.item.output}")
                elif event.item.type == "message_output_item":
                    print(
                        "-- Message output:\n "
                        f"{ItemHelpers.text_message_output(event.item)}"
                    )

    result = await race_with_workflow(render(), handle)
    print("=== Run complete ===")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
