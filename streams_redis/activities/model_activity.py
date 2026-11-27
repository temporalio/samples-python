from __future__ import annotations

import asyncio

from temporalio import activity
from temporalio.contrib.streams import BufferedAppender
from temporalio.nexus.system.stream_service import StreamRef

from streams_redis.shared import AgentEvent

ANSWER = "Redis keeps the events, so a reader can leave and come back for the rest."


@activity.defn
async def stream_answer(stream_ref: StreamRef[AgentEvent]) -> str:
    """Use fixed tokens so the sample needs no model service."""
    stream = activity.client().get_stream(stream_ref)
    # Background writes let token generation continue between flushes.
    async with BufferedAppender(stream) as tokens:
        for word in ANSWER.split():
            tokens.append(AgentEvent("token", word))
            await asyncio.sleep(0.15)
    return ANSWER
