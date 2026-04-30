from __future__ import annotations

import asyncio
import uuid

from temporalio.client import Client
from temporalio.common import RawValue
from temporalio.contrib.workflow_streams import WorkflowStreamClient

from workflow_streams.shared import (
    TASK_QUEUE,
    TOPIC_PROGRESS,
    TOPIC_STATUS,
    OrderInput,
    ProgressEvent,
    StatusEvent,
    race_with_workflow,
)
from workflow_streams.workflows.order_workflow import OrderWorkflow


async def main() -> None:
    client = await Client.connect("localhost:7233")

    workflow_id = f"workflow-stream-order-{uuid.uuid4().hex[:8]}"
    handle = await client.start_workflow(
        OrderWorkflow.run,
        OrderInput(order_id="order-1"),
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )

    stream = WorkflowStreamClient.create(client, workflow_id)
    converter = client.data_converter.payload_converter

    async def consume() -> None:
        # Single iterator over both topics — avoids a cancellation race
        # between two concurrent subscribers. result_type=RawValue
        # delivers the underlying Payload so we can dispatch
        # heterogeneous events on item.topic.
        async for item in stream.subscribe(
            [TOPIC_STATUS, TOPIC_PROGRESS], result_type=RawValue
        ):
            if item.topic == TOPIC_STATUS:
                evt = converter.from_payload(item.data.payload, StatusEvent)
                print(f"[status] {evt.kind}: order={evt.order_id}")
                if evt.kind == "complete":
                    return
            elif item.topic == TOPIC_PROGRESS:
                progress = converter.from_payload(item.data.payload, ProgressEvent)
                print(f"[progress] {progress.message}")

    result = await race_with_workflow(consume(), handle)
    print(f"workflow result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
