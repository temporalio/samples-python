from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

from temporalio.client import WorkflowHandle

TASK_QUEUE = "openai-agents-streaming-task-queue"

# Topic the plugin publishes raw model stream events to. Must match
# OpenAIAgentsPlugin(model_params=ModelActivityParameters(streaming_event_topic=...)).
TOPIC_EVENTS = "events"

# Sentinel topic the workflow publishes to once Runner.run_streamed has
# finished. Subscribers iterate (events, done) and break on the done
# event — this avoids racing handle.result() against the subscriber's
# poll cycle.
TOPIC_DONE = "done"


T = TypeVar("T")


async def race_with_workflow(
    consumer: Coroutine[Any, Any, None],
    handle: WorkflowHandle[Any, T],
) -> T:
    """Run a subscriber concurrently with the workflow.

    If the workflow finishes (success or failure) before the subscriber
    sees its sentinel, cancel the subscriber and surface the workflow
    result. If the subscriber finishes first (clean sentinel exit),
    wait for the workflow result. A non-cancellation failure in the
    subscriber is propagated either way.

    Without this, a workflow that raises before publishing the sentinel
    would leave the subscriber blocked on its next poll forever.
    """
    consumer_task = asyncio.create_task(consumer)
    result_task = asyncio.create_task(handle.result())
    we_cancelled_consumer = False
    try:
        await asyncio.wait(
            [consumer_task, result_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        # Stop the subscriber whether it reached its sentinel or not.
        if not consumer_task.done():
            consumer_task.cancel()
            we_cancelled_consumer = True
        # gather(return_exceptions=True) drains both tasks. Child
        # cancellation surfaces as a returned CancelledError; only
        # cancellation we initiated is expected — anything else
        # (including a third party cancelling the consumer behind
        # our back) propagates.
        consumer_outcome, workflow_outcome = await asyncio.gather(
            consumer_task, result_task, return_exceptions=True
        )
        if isinstance(consumer_outcome, asyncio.CancelledError):
            if not we_cancelled_consumer:
                raise consumer_outcome
        elif isinstance(consumer_outcome, BaseException):
            raise consumer_outcome
        if isinstance(workflow_outcome, BaseException):
            raise workflow_outcome
        return workflow_outcome
    finally:
        # Idempotent cleanup. try/finally re-raises the in-flight
        # exception (if any) after finally completes, so swallowing
        # cleanup failures here is safe.
        for task in (consumer_task, result_task):
            if not task.done():
                task.cancel()
        for task in (consumer_task, result_task):
            try:
                await task
            except BaseException:
                pass
