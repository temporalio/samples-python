from __future__ import annotations

from agents import Agent, Runner, function_tool, set_tracing_disabled
from temporalio import workflow


@workflow.defn
class GptOssWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        set_tracing_disabled(disabled=True)

        @function_tool
        def get_weather(city: str):
            workflow.logger.debug(f"Getting weather for {city}")
            return f"The weather in {city} is sunny."

        agent = Agent(
            name="Assistant",
            instructions="You only respond in haikus. When asked about the weather always use the tool to get the current weather..",
            model="gpt-oss:20b",
            tools=[get_weather],
        )

        result = await Runner.run(agent, prompt)
        return result.final_output
