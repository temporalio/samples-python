"""Start the agent, print its events as they come, disconnect, and resume."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable

from temporalio.client import Client
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
    """Print the events after an offset, to ``LAST_EVENT`` or ``stop_after`` of them.

    Return the events, with the offset of the last one.
    """
    events: list[AgentEvent] = []
    # The read waits for new events and never ends by itself, so the loop breaks.
    async for record in client.get_stream(stream_ref).read(from_offset=after):
        print(f"{record.offset.hex()}  {record.body.kind:<6}  {record.body.text}")
        events.append(record.body)
        after = record.offset
        if record.body == LAST_EVENT or len(events) == stop_after:
            break
    return events, after


async def run(connect: Callable[[], Awaitable[Client]]) -> list[AgentEvent]:
    client = await connect()
    handle = await client.start_workflow(
        AgentWorkflow.run,
        QUESTION,
        id=f"agent-{uuid.uuid4()}",
        task_queue=TASK_QUEUE,
    )
    stream_ref = await handle.execute_update(AgentWorkflow.stream_ref)
    first, offset = await follow(client, stream_ref, after=None, stop_after=4)
    if LAST_EVENT not in first:
        print("-- The reader disconnects, and the agent goes on.")
        await asyncio.sleep(1)

        # A new client needs only the ref and the offset, so it misses no event and
        # repeats none.
        rest, _ = await follow(await connect(), stream_ref, after=offset)
        first.extend(rest)
    print(f"-- The Workflow returned: {await handle.result()}")
    return first


if __name__ == "__main__":
    asyncio.run(run(connect))
