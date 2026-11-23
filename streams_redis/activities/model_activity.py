from __future__ import annotations

import asyncio

from temporalio import activity
from temporalio.contrib.streams import BufferedAppender
from temporalio.nexus.system.stream_service import StreamRef

from streams_redis.shared import AgentEvent

ANSWER = "Redis keeps the events, so a reader can leave and come back for the rest."


@activity.defn
async def stream_answer(stream_ref: StreamRef[AgentEvent]) -> str:
    """Stand in for a model that streams the tokens of its answer."""
    stream = activity.client().get_stream(stream_ref)
    # The appender writes in the background, so the model never waits for Redis.
    async with BufferedAppender(stream) as tokens:
        for word in ANSWER.split():
            tokens.append(AgentEvent("token", word))
            await asyncio.sleep(0.15)
    return ANSWER
