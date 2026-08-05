"""Streaming counterpart to the OpenAI Agents SDK ``stream_items.py`` example.

Adapted from https://github.com/openai/openai-agents-python/blob/main/examples/basic/stream_items.py

The upstream example renders higher-level events as they arrive: agent
updates, tool calls, tool outputs, and message outputs. Those are built by the
agents SDK from the model's output, so unlike the raw model events in
``stream_text_workflow`` they exist only inside the workflow — the streaming
activity never sees them.

So this workflow does the publishing itself: it iterates
``result.stream_events()`` and forwards each interesting event to its own
topic. ``stream_events()`` resolves a turn at a time (each model call is one
activity), so a multi-turn run like this one — model call, tool call, model
call — reaches the subscriber as a play-by-play rather than in one lump.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from agents import Agent, ItemHelpers, Runner
from temporalio import workflow
from temporalio.contrib import openai_agents as temporal_agents
from temporalio.contrib.workflow_streams import WorkflowStream, WorkflowStreamState

from openai_agents.streaming.activities.joke_activities import how_many_jokes
from openai_agents.streaming.shared import (
    DRAIN_INTERVAL,
    TOPIC_DONE,
    TOPIC_ITEMS,
    ItemEvent,
)


@dataclass
class StreamItemsInput:
    prompt: str = "Hello"
    # Carries stream state across continue-as-new. None on a fresh start.
    stream_state: WorkflowStreamState | None = None


@workflow.defn
class StreamItemsWorkflow:
    @workflow.init
    def __init__(self, input: StreamItemsInput) -> None:
        # WorkflowStream requires construction from a method named __init__
        # (it checks its caller's frame and raises otherwise), and
        # @workflow.init is what makes the run argument — and the
        # stream_state it carries across continue-as-new — available here.
        self.stream = WorkflowStream(prior_state=input.stream_state)
        self.items = self.stream.topic(TOPIC_ITEMS, type=ItemEvent)
        self.done = self.stream.topic(TOPIC_DONE, type=bool)

    @workflow.run
    async def run(self, input: StreamItemsInput) -> str:
        agent = Agent(
            name="Joker",
            instructions=(
                "First call the `how_many_jokes` tool, then tell that many jokes."
            ),
            tools=[
                temporal_agents.workflow.activity_as_tool(
                    how_many_jokes, start_to_close_timeout=timedelta(seconds=10)
                )
            ],
        )
        result = Runner.run_streamed(agent, input=input.prompt)

        messages: list[str] = []
        async for event in result.stream_events():
            if event.type == "agent_updated_stream_event":
                self.items.publish(
                    ItemEvent(kind="agent_updated", detail=event.new_agent.name)
                )
            elif event.type == "run_item_stream_event":
                item = event.item
                if item.type == "tool_call_item":
                    name = getattr(item.raw_item, "name", "Unknown Tool")
                    self.items.publish(ItemEvent(kind="tool_call", detail=name))
                elif item.type == "tool_call_output_item":
                    self.items.publish(
                        ItemEvent(kind="tool_output", detail=str(item.output))
                    )
                elif item.type == "message_output_item":
                    text = ItemHelpers.text_message_output(item)
                    messages.append(text)
                    self.items.publish(ItemEvent(kind="message_output", detail=text))

        self.done.publish(True)
        # Brief pause so the subscriber's next poll can drain the tail of the
        # stream — the log lives in workflow memory and is gone once this run
        # completes.
        await workflow.sleep(DRAIN_INTERVAL)
        # final_output is typed Any and is None when a run ends without
        # message output, so assert the str this signature promises rather
        # than letting a None through.
        if not messages:
            return result.final_output_as(str, raise_if_incorrect_type=True)
        return "\n\n".join(messages)
