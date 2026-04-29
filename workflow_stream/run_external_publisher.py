"""External publisher: a non-Activity process pushes events into a workflow.

The two earlier scenarios publish from inside the workflow itself
(``OrderWorkflow``, ``PipelineWorkflow``) or from an Activity it runs
(``charge_card``). This scenario shows the third shape: a backend
service, scheduled job, or anything else with a Temporal ``Client``
publishing into a *running* workflow it didn't start. Same factory as
the subscribe path — :py:meth:`WorkflowStreamClient.create` — used for
publishing instead.

The script starts a ``HubWorkflow`` (which does no work of its own —
it exists only to host the stream), then runs a publisher and a
subscriber concurrently. When the publisher is done it signals
``HubWorkflow.close``, the workflow's run finishes, and the
subscriber's iterator exits normally.

Run the worker first (``uv run workflow_stream/run_worker.py``), then::

    uv run workflow_stream/run_external_publisher.py
"""

from __future__ import annotations

import asyncio
import uuid

from temporalio.client import Client
from temporalio.contrib.workflow_stream import WorkflowStreamClient

from workflow_stream.shared import (
    TASK_QUEUE,
    TOPIC_NEWS,
    HubInput,
    NewsEvent,
)
from workflow_stream.workflows.hub_workflow import HubWorkflow


HEADLINES = [
    "rates held",
    "merger announced",
    "outage resolved",
    "earnings beat",
    "regulator opens probe",
]


async def main() -> None:
    client = await Client.connect("localhost:7233")

    workflow_id = f"workflow-stream-hub-{uuid.uuid4().hex[:8]}"
    handle = await client.start_workflow(
        HubWorkflow.run,
        HubInput(hub_id=workflow_id),
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )

    async def publish_news() -> None:
        # WorkflowStreamClient.create takes a Temporal client and a
        # workflow id — the same factory used elsewhere for subscribing.
        # The async context manager batches publishes and flushes on
        # exit; we additionally call flush() before signaling close so
        # we know the events landed before the workflow shuts down.
        producer = WorkflowStreamClient.create(client, workflow_id)
        async with producer:
            for headline in HEADLINES:
                producer.publish(TOPIC_NEWS, NewsEvent(headline=headline))
                print(f"[publisher] sent: {headline}")
                await asyncio.sleep(0.5)
            await producer.flush()
        # Tell the hub it can stop. The workflow's run() returns, and
        # any in-flight subscribers see their async-for loop exit.
        await handle.signal(HubWorkflow.close)
        print("[publisher] signaled close")

    async def consume_news() -> None:
        consumer = WorkflowStreamClient.create(client, workflow_id)
        async for item in consumer.subscribe(
            [TOPIC_NEWS], result_type=NewsEvent
        ):
            print(f"[subscriber] offset={item.offset}: {item.data.headline}")

    await asyncio.gather(publish_news(), consume_news())

    result = await handle.result()
    print(f"\nworkflow result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
