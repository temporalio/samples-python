from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from dataclasses import dataclass
from typing import Any, TypeVar

from temporalio.client import WorkflowHandle
from temporalio.contrib.workflow_stream import WorkflowStreamState

TASK_QUEUE = "workflow-stream-sample-task-queue"

# Topics published by the workflow / activity.
TOPIC_STATUS = "status"
TOPIC_PROGRESS = "progress"


@dataclass
class OrderInput:
    order_id: str
    # Carries stream state across continue-as-new. None on a fresh start.
    stream_state: WorkflowStreamState | None = None


@dataclass
class StatusEvent:
    kind: str
    order_id: str


@dataclass
class ProgressEvent:
    message: str


@dataclass
class PipelineInput:
    pipeline_id: str
    # Carries stream state across continue-as-new. None on a fresh start.
    stream_state: WorkflowStreamState | None = None


@dataclass
class StageEvent:
    stage: str


T = TypeVar("T")


async def race_with_workflow(
    consumer: Coroutine[Any, Any, None],
    handle: WorkflowHandle[Any, T],
) -> T:
    """Run a subscriber concurrently with the workflow.

    If the workflow finishes before the subscriber sees its terminal
    event, cancel the subscriber and surface the workflow's result
    (raising on failure). If the subscriber finishes first, wait for
    the workflow result. A non-cancellation failure in the subscriber
    is propagated either way.

    Without this, a workflow that raises before publishing its terminal
    event would leave the subscriber blocked on its next poll forever.
    """
    consumer_task = asyncio.create_task(consumer)
    result_task = asyncio.create_task(handle.result())
    we_cancelled_consumer = False
    try:
        await asyncio.wait(
            [consumer_task, result_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        if not consumer_task.done():
            consumer_task.cancel()
            we_cancelled_consumer = True
        # gather(return_exceptions=True) drains both tasks. Only
        # cancellation we initiated is expected — anything else
        # propagates.
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
        for task in (consumer_task, result_task):
            if not task.done():
                task.cancel()
        for task in (consumer_task, result_task):
            try:
                await task
            except BaseException:
                pass
