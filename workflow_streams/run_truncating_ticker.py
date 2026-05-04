"""Truncating ticker: bounded log + slow vs. fast subscribers.

The ``TickerWorkflow`` publishes ``count`` events at a fixed interval,
calling ``self.stream.truncate(...)`` periodically to bound log
growth. This script subscribes twice — once fast, once slow — and
prints them in two lanes so the trade is visible at a glance:

* **Fast lane** (left). Keeps up. Sees every published offset.
* **Slow lane** (right). Sleeps between iterations. When a truncation
  has dropped its position by the time it polls again, the iterator
  silently jumps forward to the new base offset; the slow lane prints
  a ``↪ jumped N → M (K dropped)`` marker for each gap and resumes
  at the new offset.

``truncate()`` is unilateral: the workflow does not know who is
subscribed and does not wait for them. The implicit alternative —
never truncating — keeps every event around forever, lets slow
consumers eventually catch up without losses, and pays for it in
unbounded workflow history. The truncation model is the opposite
trade: bounded log, at-best-effort delivery to slow consumers, no
backpressure on the publisher. Pair it with set-semantic events where
each event carries enough state to make missing the prior ones
recoverable. (If you actually need lossless delivery to slow
consumers, the workflow has to coordinate acknowledgements
explicitly — that is a different sample.)

Run the worker first (``uv run workflow_streams/run_worker.py``), then::

    uv run workflow_streams/run_truncating_ticker.py
"""

from __future__ import annotations

import asyncio
import uuid

from temporalio.client import Client
from temporalio.contrib.workflow_streams import WorkflowStreamClient

from workflow_streams.shared import (
    TASK_QUEUE,
    TOPIC_TICK,
    TickerInput,
    TickEvent,
)
from workflow_streams.workflows.ticker_workflow import TickerWorkflow

# Aggressive truncation so the log stays at most KEEP_LAST entries
# right after each truncation, which keeps the slow subscriber's
# per-poll batch tiny. Small batches + a slow per-event sleep mean the
# slow subscriber re-polls often, and most of those polls land after a
# truncation that has passed its position — so it sees several jumps
# during the run rather than one batched at the end.
TICKER_COUNT = 30
INTERVAL_MS = 200
TRUNCATE_EVERY = 2
KEEP_LAST = 1
SLOW_SUBSCRIBER_DELAY_S = 1.5

LANE_WIDTH = 32
SEP = "│"


def emit_fast(message: str) -> None:
    print(f"{message:<{LANE_WIDTH}} {SEP}", flush=True)


def emit_slow(message: str) -> None:
    print(f"{' ' * LANE_WIDTH} {SEP} {message}", flush=True)


def emit_header() -> None:
    rule = "─" * LANE_WIDTH
    print(
        f"{'fast (every event)':<{LANE_WIDTH}} {SEP} "
        f"slow (sleeps {SLOW_SUBSCRIBER_DELAY_S}s between events)"
    )
    print(f"{rule} {SEP} {rule}")


async def main() -> None:
    client = await Client.connect("localhost:7233")

    workflow_id = f"workflow-stream-ticker-{uuid.uuid4().hex[:8]}"
    handle = await client.start_workflow(
        TickerWorkflow.run,
        TickerInput(
            count=TICKER_COUNT,
            keep_last=KEEP_LAST,
            truncate_every=TRUNCATE_EVERY,
            interval_ms=INTERVAL_MS,
        ),
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )
    stream = WorkflowStreamClient.create(client, workflow_id)
    last_n = TICKER_COUNT - 1

    emit_header()

    async def fast_subscriber() -> None:
        async for item in stream.subscribe([TOPIC_TICK], result_type=TickEvent):
            emit_fast(f"offset={item.offset:>3}  n={item.data.n}")
            if item.data.n == last_n:
                return

    async def slow_subscriber() -> None:
        last_offset = -1
        async for item in stream.subscribe([TOPIC_TICK], result_type=TickEvent):
            if last_offset >= 0 and item.offset > last_offset + 1:
                gap = item.offset - last_offset - 1
                emit_slow(
                    f"↪ jumped offset={last_offset} → {item.offset} ({gap} dropped)"
                )
            emit_slow(f"offset={item.offset:>3}  n={item.data.n}")
            last_offset = item.offset
            if item.data.n == last_n:
                return
            await asyncio.sleep(SLOW_SUBSCRIBER_DELAY_S)

    await asyncio.gather(fast_subscriber(), slow_subscriber())

    result = await handle.result()
    print()
    print(f"workflow result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
