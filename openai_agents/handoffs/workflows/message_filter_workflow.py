from __future__ import annotations

from dataclasses import dataclass
from typing import List

from agents import Agent, HandoffInputData, Runner, function_tool, handoff
from agents.extensions import handoff_filters
from agents.items import TResponseInputItem
from temporalio import workflow


@dataclass
class MessageFilterResult:
    final_output: str
    final_messages: List[TResponseInputItem]


@function_tool
def random_number_tool(max: int) -> int:
    """Return a random integer between 0 and the given maximum."""
    return workflow.random().randint(0, max)


def spanish_handoff_message_filter(
    handoff_message_data: HandoffInputData,
) -> HandoffInputData:
    # First, we'll remove any tool-related messages from the message history
    handoff_message_data = handoff_filters.remove_all_tools(handoff_message_data)

    # Second, we'll also remove the first two items from the history, just for demonstration
    history = (
        tuple(handoff_message_data.input_history[2:])
        if isinstance(handoff_message_data.input_history, tuple)
        else handoff_message_data.input_history
    )

    return HandoffInputData(
        input_history=history,
        pre_handoff_items=tuple(handoff_message_data.pre_handoff_items),
        new_items=tuple(handoff_message_data.new_items),
    )


@workflow.defn
class MessageFilterWorkflow:
    @workflow.run
    async def run(self, user_name: str = "Sora") -> MessageFilterResult:
        first_agent = Agent(
            name="Assistant",
            instructions="Be extremely concise.",
            tools=[random_number_tool],
        )

        spanish_agent = Agent(
            name="Spanish Assistant",
            instructions="You only speak Spanish and are extremely concise.",
            handoff_description="A Spanish-speaking assistant.",
        )

        second_agent = Agent(
            name="Assistant",
            instructions=(
                "Be a helpful assistant. If the user speaks Spanish, handoff to the Spanish assistant."
            ),
            handoffs=[
                handoff(spanish_agent, input_filter=spanish_handoff_message_filter)
            ],
        )

        # 1. Send a regular message to the first agent
        result = await Runner.run(first_agent, input=f"Hi, my name is {user_name}.")

        # 2. Ask it to generate a number
        result = await Runner.run(
            first_agent,
            input=result.to_input_list()
            + [
                {
                    "content": "Can you generate a random number between 0 and 100?",
                    "role": "user",
                }
            ],
        )

        # 3. Call the second agent
        result = await Runner.run(
            second_agent,
            input=result.to_input_list()
            + [
                {
                    "content": "I live in New York City. What's the population of the city?",
                    "role": "user",
                }
            ],
        )

        # 4. Cause a handoff to occur
        result = await Runner.run(
            second_agent,
            input=result.to_input_list()
            + [
                {
                    "content": "Por favor habla en español. ¿Cuál es mi nombre y dónde vivo?",
                    "role": "user",
                }
            ],
        )

        # Return the final result and message history
        return MessageFilterResult(
            final_output=result.final_output, final_messages=result.to_input_list()
        )
