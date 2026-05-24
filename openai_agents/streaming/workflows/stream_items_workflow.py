from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from agents import Agent, ItemHelpers, Runner
from temporalio import workflow
from temporalio.contrib import openai_agents as temporal_agents
from temporalio.contrib.workflow_streams import WorkflowStream, WorkflowStreamState

from openai_agents.streaming.activities.joke_activities import how_many_jokes
from openai_agents.streaming.shared import TOPIC_DONE

"""Streaming counterpart to the OpenAI Agents SDK ``stream_items.py`` example.

Adapted from https://github.com/openai/openai-agents-python/blob/main/examples/basic/stream_items.py

This variant streams higher-level events: tool calls, tool outputs,
agent updates, and message outputs. External subscribers can render a
play-by-play of the agent's reasoning as it unfolds, while the workflow
itself just waits for the final answer.
"""


@dataclass
class StreamItemsInput:
    stream_state: WorkflowStreamState | None = None


@workflow.defn
class StreamItemsWorkflow:
    @workflow.init
    def __init__(self, input: StreamItemsInput) -> None:
        self.stream = WorkflowStream(prior_state=input.stream_state)
        self.done = self.stream.topic(TOPIC_DONE, type=type(None))

    @workflow.run
    async def run(self, input: StreamItemsInput) -> str:
        del input  # only used in @workflow.init for prior_state
        agent = Agent(
            name="Joker",
            instructions=(
                "First call the `how_many_jokes` tool, "
                "then tell that many jokes."
            ),
            tools=[
                temporal_agents.workflow.activity_as_tool(
                    how_many_jokes, start_to_close_timeout=timedelta(seconds=10)
                )
            ],
        )
        result = Runner.run_streamed(agent, input="Hello")

        messages: list[str] = []
        async for event in result.stream_events():
            if event.type == "run_item_stream_event" and event.item.type == (
                "message_output_item"
            ):
                messages.append(ItemHelpers.text_message_output(event.item))
        # Sentinel for the external subscriber.
        self.done.publish(None)
        return "\n\n".join(messages) if messages else result.final_output
