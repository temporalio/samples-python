from typing import Any

from agents import Agent, AgentHooks, RunContextWrapper, Runner, function_tool
from pydantic import BaseModel
from temporalio import workflow


class CustomAgentHooks(AgentHooks):
    def __init__(self, display_name: str):
        self.event_counter = 0
        self.display_name = display_name

    async def on_start(self, context: RunContextWrapper, agent: Agent) -> None:
        self.event_counter += 1
        print(
            f"### ({self.display_name}) {self.event_counter}: Agent {agent.name} started"
        )

    async def on_end(
        self, context: RunContextWrapper, agent: Agent, output: Any
    ) -> None:
        self.event_counter += 1
        print(
            f"### ({self.display_name}) {self.event_counter}: Agent {agent.name} ended with output {output}"
        )

    async def on_handoff(
        self, context: RunContextWrapper, agent: Agent, source: Agent
    ) -> None:
        self.event_counter += 1
        print(
            f"### ({self.display_name}) {self.event_counter}: Agent {source.name} handed off to {agent.name}"
        )

    async def on_tool_start(
        self, context: RunContextWrapper, agent: Agent, tool
    ) -> None:
        self.event_counter += 1
        print(
            f"### ({self.display_name}) {self.event_counter}: Agent {agent.name} started tool {tool.name}"
        )

    async def on_tool_end(
        self, context: RunContextWrapper, agent: Agent, tool, result: str
    ) -> None:
        self.event_counter += 1
        print(
            f"### ({self.display_name}) {self.event_counter}: Agent {agent.name} ended tool {tool.name} with result {result}"
        )


@function_tool
def random_number_tool(max: int) -> int:
    """
    Generate a random number up to the provided maximum.
    """
    return workflow.random().randint(0, max)


@function_tool
def multiply_by_two_tool(x: int) -> int:
    """Simple multiplication by two."""
    return x * 2


class FinalResult(BaseModel):
    number: int


@workflow.defn
class AgentLifecycleWorkflow:
    @workflow.run
    async def run(self, max_number: int) -> FinalResult:
        multiply_agent = Agent(
            name="Multiply Agent",
            instructions="Multiply the number by 2 and then return the final result.",
            tools=[multiply_by_two_tool],
            output_type=FinalResult,
            hooks=CustomAgentHooks(display_name="Multiply Agent"),
        )

        start_agent = Agent(
            name="Start Agent",
            instructions="Generate a random number. If it's even, stop. If it's odd, hand off to the multiply agent.",
            tools=[random_number_tool],
            output_type=FinalResult,
            handoffs=[multiply_agent],
            hooks=CustomAgentHooks(display_name="Start Agent"),
        )

        result = await Runner.run(
            start_agent,
            input=f"Generate a random number between 0 and {max_number}.",
        )

        return result.final_output
