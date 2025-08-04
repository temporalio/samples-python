from __future__ import annotations

from agents import Agent, Runner, function_tool, set_tracing_disabled
from temporalio import workflow


@workflow.defn
class LitellmAutoWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        set_tracing_disabled(disabled=True)

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
