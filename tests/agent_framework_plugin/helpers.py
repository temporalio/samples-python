"""Shared helpers for the Agent Framework plugin sample tests."""

import json
from collections import Counter
from collections.abc import Sequence
from typing import Any

from agent_framework import Message
from temporalio.agent_framework import AgentFrameworkPlugin
from temporalio.api.enums.v1 import EventType
from temporalio.client import Client, WorkflowHandle

INVOKE_MODEL = "agent_framework.invoke_model"
INVOKE_MODEL_STREAMING = "agent_framework.invoke_model_streaming"


def with_plugin(client: Client, plugin: AgentFrameworkPlugin) -> Client:
    """Return a client with ``plugin`` added after the environment's own plugins."""
    config = client.config()
    config["plugins"] = [*config["plugins"], plugin]
    return Client(**config)


async def count_scheduled_activities(handle: WorkflowHandle) -> Counter[str]:
    """Count ``ActivityTaskScheduled`` events in the history by activity type.

    The plugin's whole point is that model, tool and MCP calls run as
    Activities. Asserting on the history proves that routing happened, where a
    content-only assertion would still pass if a call silently ran in the
    Workflow.
    """
    counts: Counter[str] = Counter()
    async for event in handle.fetch_history_events():
        if event.event_type == EventType.EVENT_TYPE_ACTIVITY_TASK_SCHEDULED:
            counts[
                event.activity_task_scheduled_event_attributes.activity_type.name
            ] += 1
    return counts


async def activity_summaries(handle: WorkflowHandle) -> list[str | None]:
    """Return the ``summary`` of each ``ActivityTaskScheduled`` event, in order."""
    summaries: list[str | None] = []
    async for event in handle.fetch_history_events():
        if event.event_type != EventType.EVENT_TYPE_ACTIVITY_TASK_SCHEDULED:
            continue
        if event.HasField("user_metadata") and event.user_metadata.HasField("summary"):
            summaries.append(json.loads(event.user_metadata.summary.data))
        else:
            summaries.append(None)
    return summaries


def function_results(messages: Sequence[Message]) -> list[str]:
    """Return every function result in ``messages`` as text, in order."""
    results: list[str] = []
    for message in messages:
        for content in message.contents:
            if content.type == "function_result":
                results.append(_result_text(content.result))
    return results


def _result_text(result: Any) -> str:
    if isinstance(result, str):
        return result
    if isinstance(result, list):
        return "".join(getattr(item, "text", "") or "" for item in result)
    return json.dumps(result, default=str)
