"""Truncating ticker: bounded log + slow vs. fast subscribers.

The ``TickerWorkflow`` publishes ``count`` events at a fixed interval,
calling ``self.stream.truncate(...)`` periodically to bound log
growth. This script subscribes twice — once fast, once slow — and
prints both side-by-side so the trade is visible:

* The fast subscriber keeps up and sees every published offset in
  order.
* The slow subscriber sleeps between iterations. When a truncation
  runs past its position, the iterator silently jumps forward to the
  new base offset — the slow subscriber's offsets jump too, and
  intermediate events are not visible to it.

This is the bounded-log model: log size is capped, slow consumers may
miss intermediate events, but they always see the most recent state.
For long-running workflows pushing high event volumes this is usually
the right trade — pair with set-semantic events where each event
carries enough state to make missing the prior ones recoverable.

Run the worker first (``uv run workflow_stream/run_worker.py``), then::

    uv run workflow_stream/run_truncating_ticker.py
"""

from __future__ import annotations

import asyncio
import uuid

from temporalio.client import Client
from temporalio.contrib.workflow_stream import WorkflowStreamClient

from workflow_stream.shared import (
    TASK_QUEUE,
    TOPIC_TICK,
    TickerInput,
    TickEvent,
)
from workflow_stream.workflows.ticker_workflow import TickerWorkflow


SLOW_SUBSCRIBER_DELAY_S = 1.5


async def main() -> None:
    client = await Client.connect("localhost:7233")

    workflow_id = f"workflow-stream-ticker-{uuid.uuid4().hex[:8]}"
    handle = await client.start_workflow(
        TickerWorkflow.run,
        TickerInput(
            count=20,
            keep_last=3,
            truncate_every=5,
            interval_ms=400,
        ),
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )

    stream = WorkflowStreamClient.create(client, workflow_id)

    async def fast_subscriber() -> None:
        async for item in stream.subscribe([TOPIC_TICK], result_type=TickEvent):
            print(f"[fast]  offset={item.offset:3d}  n={item.data.n}")

    async def slow_subscriber() -> None:
        async for item in stream.subscribe([TOPIC_TICK], result_type=TickEvent):
            print(f"[SLOW]  offset={item.offset:3d}  n={item.data.n}")
            await asyncio.sleep(SLOW_SUBSCRIBER_DELAY_S)

    # Both iterators exit normally when the workflow completes. No
    # terminal sentinel is needed — see the doc's "When the Workflow
    # run completes" note.
    await asyncio.gather(fast_subscriber(), slow_subscriber())

    result = await handle.result()
    print(f"\nworkflow result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
