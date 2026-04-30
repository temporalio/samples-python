from __future__ import annotations

from dataclasses import dataclass

from agents import Agent, Runner
from openai.types.responses import ResponseTextDeltaEvent
from temporalio import workflow
from temporalio.contrib.workflow_streams import WorkflowStream, WorkflowStreamState

from openai_agents.streaming.shared import TOPIC_DONE

"""Streaming counterpart to the OpenAI Agents SDK ``stream_text.py`` example.

Adapted from https://github.com/openai/openai-agents-python/blob/main/examples/basic/stream_text.py

The upstream example calls ``Runner.run_streamed`` and iterates raw
``ResponseTextDeltaEvent``s as they arrive over HTTP. Inside a Temporal
workflow the model call runs in an activity, so the workflow cannot
iterate the live HTTP stream directly. The plugin's streaming support
runs ``model.stream_response()`` inside the activity and publishes each
``TResponseStreamEvent`` to the workflow's stream. Events are coalesced
into batches over ``streaming_event_batch_interval`` (default 100ms)
before being delivered to subscribers as signals — buffered token
streaming, not per-token. Output arrives in small bursts; the cadence
is visible compared to a true per-token render but is close enough for
most UIs.

The workflow itself only needs to:

1. host a ``WorkflowStream`` so the activity has somewhere to publish to;
2. call ``Runner.run_streamed`` (rather than ``Runner.run``) so the agent
   framework drives the streaming activity.

In a Temporal workflow ``stream_events()`` resolves only after the
underlying activity returns, so any in-workflow consumption is on the
final list — not deltas-as-they-arrive.
"""


@dataclass
class StreamTextInput:
    prompt: str
    stream_state: WorkflowStreamState | None = None


@workflow.defn
class StreamTextWorkflow:
    @workflow.init
    def __init__(self, input: StreamTextInput) -> None:
        # Required: the streaming activity publishes to this stream.
        # Without it, the publish signals are unhandled and dropped.
        self.stream = WorkflowStream(prior_state=input.stream_state)
        self.done = self.stream.topic(TOPIC_DONE, type=type(None))

    @workflow.run
    async def run(self, input: StreamTextInput) -> str:
        agent = Agent(
            name="Joker",
            instructions="You are a helpful assistant.",
        )
        result = Runner.run_streamed(agent, input=input.prompt)

        # Runner.run_streamed launches the agent loop in a background
        # task; iterating consumes from it and waits for completion.
        # The workflow side only sees the events once the activity
        # returns, so this loop accumulates a count for logging.
        # External subscribers receive them as the activity publishes.
        deltas = 0
        async for event in result.stream_events():
            if event.type == "raw_response_event" and isinstance(
                event.data, ResponseTextDeltaEvent
            ):
                deltas += 1
        workflow.logger.info("collected %d delta events", deltas)
        # Sentinel for the external subscriber. Without it the
        # subscriber's async iterator would block on its next poll
        # waiting for events that never come.
        self.done.publish(None)
        return result.final_output
