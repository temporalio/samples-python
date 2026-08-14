"""Shared helpers for the Deep Agents plugin sample tests."""

from collections import Counter

from temporalio.api.enums.v1 import EventType
from temporalio.client import WorkflowHandle

INVOKE_MODEL = "deepagents.invoke_model"
INVOKE_MODEL_STREAMING = "deepagents.invoke_model_streaming"
INVOKE_TOOL = "deepagents.invoke_tool"
BACKEND_OP = "deepagents.backend_op"


async def count_scheduled_activities(handle: WorkflowHandle) -> Counter:
    """Count ``ActivityTaskScheduled`` events in the history by activity type.

    The plugin's whole point is that model/tool/backend calls run as activities;
    asserting on the history proves that routing actually happened, where a
    content-only assertion would still pass if a call silently ran in-workflow.
    """
    counts: Counter = Counter()
    async for event in handle.fetch_history_events():
        if event.event_type == EventType.EVENT_TYPE_ACTIVITY_TASK_SCHEDULED:
            counts[
                event.activity_task_scheduled_event_attributes.activity_type.name
            ] += 1
    return counts
