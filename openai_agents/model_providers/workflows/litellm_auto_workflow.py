from __future__ import annotations

from agents import Agent, Runner, function_tool
from temporalio import workflow


@workflow.defn
class LitellmAutoWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        @function_tool
        def get_weather(city: str):
            return f"The weather in {city} is sunny."

        agent = Agent(
            name="Assistant",
            instructions="You only respond in haikus.",
            model="anthropic/claude-3-5-sonnet-20240620",
            tools=[get_weather],
        )

        result = await Runner.run(agent, prompt)
        return result.final_output
