from __future__ import annotations

import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.nexus.system.stream_service import StreamRef

with workflow.unsafe.imports_passed_through():
    from streams_redis.activities.model_activity import stream_answer
    from streams_redis.shared import LAST_EVENT, AgentEvent


@workflow.defn
class AgentWorkflow:
    def __init__(self) -> None:
        self._stream_ref: StreamRef[AgentEvent] | None = None

    @workflow.update
    async def stream_ref(self) -> StreamRef[AgentEvent]:
        # A read of a Stream that doesn't exist yet fails, so a reader waits here.
        await workflow.wait_condition(lambda: self._stream_ref is not None)
        assert self._stream_ref
        return self._stream_ref

    @workflow.run
    async def run(self, question: str) -> str:
        stream = await workflow.create_stream(
            id=workflow.info().workflow_id, body_type=AgentEvent
        )
        self._stream_ref = stream.ref
        try:
            await stream.append(AgentEvent("status", f"Thinking about: {question}"))
            # Cancellation must preserve the recorded Workflow command order.
            wait_for_writer = workflow.patched("wait-for-stream-writer-cancellation")
            result = await workflow.execute_activity(
                stream_answer,
                stream.ref,
                start_to_close_timeout=timedelta(minutes=1),
                heartbeat_timeout=timedelta(seconds=1) if wait_for_writer else None,
                cancellation_type=(
                    workflow.ActivityCancellationType.WAIT_CANCELLATION_COMPLETED
                    if wait_for_writer
                    else workflow.ActivityCancellationType.TRY_CANCEL
                ),
            )
        except (Exception, asyncio.CancelledError):
            # Coroutine cleanup cannot await a Store call, so exclude GeneratorExit.
            await stream.append(LAST_EVENT)
            raise
        await stream.append(LAST_EVENT)
        return result
