from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

TASK_QUEUE = "openai-agents-streaming-task-queue"

# Topic the streaming activity publishes raw model stream events to. Must match
# OpenAIAgentsPlugin(model_params=ModelActivityParameters(streaming_topic=...)).
# Events on this topic are native OpenAI `TResponseStreamEvent`s, not the
# agents-SDK `StreamEvent` wrappers that `stream_events()` yields.
TOPIC_EVENTS = "events"

# Topic the stream_items workflow publishes its own higher-level events to. The
# agents SDK builds those from the model output inside the workflow, so the
# workflow — not the activity — is what publishes them.
TOPIC_ITEMS = "items"

# Topic the workflow publishes a terminator to once Runner.run_streamed has
# finished. Subscribers watch both topics and break on the terminator, rather
# than racing handle.result() against their next poll.
TOPIC_DONE = "done"

# How long a workflow holds its run open after publishing the terminator, so a
# subscriber's next poll can drain the tail of the stream. The log lives in
# workflow memory, so it disappears when the run completes.
DRAIN_INTERVAL = timedelta(milliseconds=500)


@dataclass
class ItemEvent:
    """One step of a run, as published on TOPIC_ITEMS.

    The agents-SDK event types (`RunItemStreamEvent` and friends) carry the
    originating `Agent`, which holds tool callables and so is not
    serializable. Samples publish their own flattened event instead.
    """

    kind: str
    """One of "agent_updated", "tool_call", "tool_output", "message_output"."""

    detail: str
