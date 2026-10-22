"""Streaming counterpart to the OpenAI Agents SDK ``stream_text.py`` example.

Adapted from https://github.com/openai/openai-agents-python/blob/main/examples/basic/stream_text.py

The upstream example calls ``Runner.run_streamed`` and iterates raw
``ResponseTextDeltaEvent``s as they arrive over HTTP. Inside a Temporal
workflow the model call runs in an activity, so the workflow cannot iterate
the live HTTP stream directly. The plugin's streaming support runs
``model.stream_response()`` inside the activity and publishes each event to
the workflow's stream, where external subscribers see them as they are
produced.

The workflow itself only needs to:

1. host a ``WorkflowStream`` so the streaming activity has somewhere to
   publish to;
2. call ``Runner.run_streamed`` (rather than ``Runner.run``) so the agents
   framework drives the streaming activity.

``stream_events()`` inside the workflow resolves only once the activity
returns, so in-workflow consumption is over the final list — not
deltas-as-they-arrive. Streaming is for external observers.
"""

from __future__ import annotations

from dataclasses import dataclass

from agents import Agent, Runner
from openai.types.responses import ResponseTextDeltaEvent
from temporalio import workflow
from temporalio.contrib.workflow_streams import WorkflowStream, WorkflowStreamState

from openai_agents.streaming.shared import DRAIN_INTERVAL, TOPIC_DONE


@dataclass
class StreamTextInput:
    prompt: str
    # Carries stream state across continue-as-new. None on a fresh start.
    stream_state: WorkflowStreamState | None = None


# @@@SNIPSTART python-openai-agents-streaming-workflow
@workflow.defn
class StreamTextWorkflow:
    @workflow.init
    def __init__(self, input: StreamTextInput) -> None:
        # WorkflowStream requires construction from a method named __init__
        # (it checks its caller's frame and raises otherwise), and
        # @workflow.init is what makes the run argument — and the
        # stream_state it carries across continue-as-new — available here.
        self.stream = WorkflowStream(prior_state=input.stream_state)
        self.done = self.stream.topic(TOPIC_DONE, type=bool)

    @workflow.run
    async def run(self, input: StreamTextInput) -> str:
        agent = Agent(
            name="Joker",
            instructions="You are a helpful assistant.",
        )
        result = Runner.run_streamed(agent, input=input.prompt)

        # The workflow only sees these events once the activity returns, so
        # the loop just counts them. External subscribers receive them as the
        # activity publishes them.
        deltas = 0
        async for event in result.stream_events():
            if event.type == "raw_response_event" and isinstance(
                event.data, ResponseTextDeltaEvent
            ):
                deltas += 1
        workflow.logger.info("collected %d delta events", deltas)

        # In-band terminator so the subscriber can stop without racing the
        # workflow's completion, then a brief pause to let its next poll
        # deliver the tail of the stream — the log lives in workflow memory
        # and is gone once this run completes.
        self.done.publish(True)
        await workflow.sleep(DRAIN_INTERVAL)
        # final_output is typed Any and is None when a run ends without
        # message output, so assert the str this signature promises rather
        # than letting a None through.
        return result.final_output_as(str, raise_if_incorrect_type=True)


# @@@SNIPEND
