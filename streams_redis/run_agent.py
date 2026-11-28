"""Resume Stream reads after a client disconnect."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable

from temporalio.client import (
    Client,
    WithStartWorkflowOperation,
    WorkflowUpdateHandle,
    WorkflowUpdateStage,
)
from temporalio.common import WorkflowIDConflictPolicy
from temporalio.nexus.system.stream_service import StreamRef

from streams_redis.shared import LAST_EVENT, TASK_QUEUE, AgentEvent, connect
from streams_redis.workflows.agent_workflow import AgentWorkflow

QUESTION = "Why keep the events of an agent in Redis?"


async def follow(
    client: Client,
    stream_ref: StreamRef[AgentEvent],
    after: bytes | None,
    stop_after: int | None = None,
) -> tuple[list[AgentEvent], bytes | None]:
    """Stop at an application event because Streams have no close operation."""
    events: list[AgentEvent] = []
    async for record in client.get_stream(stream_ref).read(from_offset=after):
        print(f"{record.offset.hex()}  {record.body.kind:<6}  {record.body.text}")
        events.append(record.body)
        after = record.offset
        if record.body == LAST_EVENT or len(events) == stop_after:
            break
    return events, after


async def read_and_resume(
    client: Client,
    ref_update: WorkflowUpdateHandle[StreamRef[AgentEvent]],
    connect: Callable[[], Awaitable[Client]],
) -> list[AgentEvent]:
    stream_ref = await ref_update.result()
    first, offset = await follow(client, stream_ref, after=None, stop_after=4)
    if LAST_EVENT not in first:
        print("-- The reader disconnects, and the agent goes on.")
        await asyncio.sleep(1)

        # The last consumed offset prevents gaps and repeats after reconnect.
        rest, _ = await follow(await connect(), stream_ref, after=offset)
        first.extend(rest)
    return first


async def run(connect: Callable[[], Awaitable[Client]]) -> list[AgentEvent]:
    client = await connect()
    start = WithStartWorkflowOperation(
        AgentWorkflow.run,
        QUESTION,
        id=f"agent-{uuid.uuid4()}",
        id_conflict_policy=WorkflowIDConflictPolicy.FAIL,
        task_queue=TASK_QUEUE,
    )
    ref_update = await client.start_update_with_start_workflow(
        AgentWorkflow.stream_ref,
        start_workflow_operation=start,
        wait_for_stage=WorkflowUpdateStage.ACCEPTED,
    )
    handle = await start.workflow_handle()
    result_task = asyncio.create_task(handle.result())
    reader_task = asyncio.create_task(read_and_resume(client, ref_update, connect))
    try:
        # Termination skips the Workflow's final event, so also observe its result.
        done, _ = await asyncio.wait(
            (reader_task, result_task), return_when=asyncio.FIRST_COMPLETED
        )
        if result_task in done:
            await result_task
        events = await reader_task
        print(f"-- The Workflow returned: {await result_task}")
        return events
    finally:
        for task in (reader_task, result_task):
            task.cancel()
        await asyncio.gather(reader_task, result_task, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(run(connect))
