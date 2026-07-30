"""Reconnecting subscriber: read a few events, disconnect, resume.

Demonstrates the central Workflow Streams use case: a consumer can
disappear mid-stream — page refresh, server restart, laptop closed —
and resume later without missing events or seeing duplicates. The
event log lives in the Workflow, so the consumer just remembers where
it stopped.

The script runs the pattern in two phases inside one process to keep
the demo short. The same code shape works across actual process
restarts because the resume offset is durable in the workflow, not in
the consumer.

Output is one line per emit, with current stream stats in a left column
and a phase / event message in a right column. A background poller
calls ``WorkflowStreamClient.get_offset()`` for the whole demo and
emits a heartbeat line once a second so you can watch ``pending``
(``available - processed``) grow while the consumer is disconnected
and shrink as phase 2 catches up.

Run the worker first (``uv run workflow_streams/run_worker.py``), then::

    uv run workflow_streams/run_reconnecting_subscriber.py
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass

from temporalio.client import Client
from temporalio.contrib.workflow_streams import WorkflowStreamClient

from workflow_streams.shared import (
    TASK_QUEUE,
    TOPIC_STATUS,
    PipelineInput,
    StageEvent,
)
from workflow_streams.workflows.pipeline_workflow import PipelineWorkflow

# Number of events read in phase 1 before simulating a disconnect.
# Picked small enough that the workflow is still running after.
PHASE_1_EVENTS = 2

# How long to stay disconnected.
DISCONNECT_SECONDS = 3.0

# Background poller cadence. The poller refreshes state.available this
# often and emits a heartbeat line once per HEARTBEAT_SECONDS.
POLL_INTERVAL_SECONDS = 0.25
HEARTBEAT_SECONDS = 1.0

# Width of the stats column. Picked to fit the longest stats string.
LEFT_WIDTH = 30


@dataclass
class State:
    processed: int = 0
    available: int = 0

    @property
    def pending(self) -> int:
        return max(0, self.available - self.processed)


def emit(state: State, message: str) -> None:
    left = (
        f"proc={state.processed:>2}  "
        f"avail={state.available:>2}  "
        f"pend={state.pending:>2}"
    )
    print(f"{left:<{LEFT_WIDTH}}│ {message}", flush=True)


async def main() -> None:
    client = await Client.connect("localhost:7233")

    workflow_id = f"workflow-stream-pipeline-{uuid.uuid4().hex[:8]}"
    handle = await client.start_workflow(
        PipelineWorkflow.run,
        PipelineInput(pipeline_id=workflow_id),
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )

    # In a production web backend the resume offset would live in
    # durable storage keyed by (user_id, run_id) — a database row, a
    # Redis key, etc. For an in-process demo a State.processed
    # attribute works the same way.
    state = State()
    stream = WorkflowStreamClient.create(client, workflow_id)
    emit(state, f"started {workflow_id}")

    stop = asyncio.Event()

    async def poller() -> None:
        """Refresh state.available; emit a heartbeat line once a second."""
        loop = asyncio.get_running_loop()
        last_emit = loop.time()
        while not stop.is_set():
            try:
                state.available = await stream.get_offset()
            except Exception:
                pass
            now = loop.time()
            if now - last_emit >= HEARTBEAT_SECONDS:
                emit(state, "·")
                last_emit = now
            try:
                await asyncio.wait_for(stop.wait(), timeout=POLL_INTERVAL_SECONDS)
            except asyncio.TimeoutError:
                pass

    poller_task = asyncio.create_task(poller())
    try:
        # ---- Phase 1: connect, read a couple of events, "disconnect".
        emit(state, "[phase 1] connecting")
        seen = 0
        async for item in stream.subscribe([TOPIC_STATUS], result_type=StageEvent):
            # Remember *one past* the offset just consumed: on resume we
            # want the next unseen event, not the one we already showed.
            state.processed = item.offset + 1
            emit(state, f"  offset={item.offset:2d}  stage={item.data.stage}")
            seen += 1
            if seen >= PHASE_1_EVENTS:
                break
        emit(state, "[phase 1] disconnecting")

        # ---- Disconnect window: nobody reads. The workflow keeps
        # publishing — `pend` grows on the heartbeat lines as the offset
        # advances past `processed`.
        await asyncio.sleep(DISCONNECT_SECONDS)

        # ---- Phase 2: brand-new client + stream, resume from saved
        # offset. Same shape as a different process picking up where the
        # first one left off.
        emit(state, "[phase 2] reconnecting")
        client2 = await Client.connect("localhost:7233")
        stream2 = WorkflowStreamClient.create(client2, workflow_id)
        async for item in stream2.subscribe(
            [TOPIC_STATUS],
            from_offset=state.processed,
            result_type=StageEvent,
        ):
            state.processed = item.offset + 1
            emit(state, f"  offset={item.offset:2d}  stage={item.data.stage}")
            if item.data.stage == "complete":
                break

        result = await handle.result()
        emit(state, f"workflow result: {result}")
    finally:
        stop.set()
        try:
            await poller_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    asyncio.run(main())
