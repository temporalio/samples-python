"""Reconnecting subscriber: persist offset, disconnect, resume.

Demonstrates the central Workflow Streams use case: a consumer can
disappear mid-stream — page refresh, server restart, laptop closed —
and resume later without missing events or seeing duplicates. The
event log lives in the Workflow, so the consumer just remembers where
it stopped.

The script runs the pattern in two phases inside one process to keep
the demo short. The same code shape works across actual process
restarts because the resume offset is persisted to disk between phases.

Run the worker first (``uv run workflow_streams/run_worker.py``), then::

    uv run workflow_streams/run_reconnecting_subscriber.py
"""

from __future__ import annotations

import asyncio
import tempfile
import uuid
from pathlib import Path

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


async def main() -> None:
    client = await Client.connect("localhost:7233")

    workflow_id = f"workflow-stream-pipeline-{uuid.uuid4().hex[:8]}"
    handle = await client.start_workflow(
        PipelineWorkflow.run,
        PipelineInput(pipeline_id=workflow_id),
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )

    # Where the consumer remembers its position. In a real BFF or UI
    # backend this would be a database row keyed by (user_id, run_id);
    # a temp file keeps the sample self-contained.
    offset_path = Path(tempfile.gettempdir()) / f"{workflow_id}.offset"

    # ---- Phase 1: connect, read a couple of events, persist offset, disconnect.
    print("[phase 1] connecting and reading first few events")
    stream = WorkflowStreamClient.create(client, workflow_id)
    seen = 0
    next_offset = 0
    async for item in stream.subscribe([TOPIC_STATUS], result_type=StageEvent):
        print(f"  offset={item.offset:2d}  stage={item.data.stage}")
        # Persist *one past* the offset just consumed. On resume we want
        # the *next* unseen event, not the one we already showed.
        next_offset = item.offset + 1
        offset_path.write_text(str(next_offset))
        seen += 1
        if seen >= PHASE_1_EVENTS:
            break

    print(
        f"[phase 1] persisted resume offset={next_offset} -> {offset_path}; disconnecting\n"
    )
    # The async for loop exits the subscribe() iterator. Any background
    # poll Update is cancelled. The workflow keeps running in the
    # background, accumulating events into its log.
    await asyncio.sleep(3)  # let the workflow publish more in our absence

    # ---- Phase 2: reconnect, read persisted offset, resume from there.
    print("[phase 2] reconnecting and resuming from persisted offset")
    resume_from = int(offset_path.read_text())
    # A brand-new client and stream object — same shape as a different
    # process picking up where the first one left off.
    client2 = await Client.connect("localhost:7233")
    stream2 = WorkflowStreamClient.create(client2, workflow_id)
    async for item in stream2.subscribe(
        [TOPIC_STATUS],
        from_offset=resume_from,
        result_type=StageEvent,
    ):
        print(f"  offset={item.offset:2d}  stage={item.data.stage}")
        # Continue persisting after each event so a second crash here
        # would also resume cleanly.
        offset_path.write_text(str(item.offset + 1))
        if item.data.stage == "complete":
            break

    result = await handle.result()
    print(f"\nworkflow result: {result}")
    # Clean up the offset file; in a real consumer you'd retain it as
    # long as the user might reconnect.
    offset_path.unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())
