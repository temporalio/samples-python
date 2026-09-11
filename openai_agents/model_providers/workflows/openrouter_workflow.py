from __future__ import annotations

from agents import Agent, Runner, function_tool
from temporalio import workflow

# Any OpenRouter model slug works here. A fixed, tool-capable model keeps the
# sample reproducible; swap in "openrouter/auto" to let OpenRouter choose.
OPENROUTER_MODEL = "openai/gpt-4o-mini"


@workflow.defn
class OpenRouterAgentWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        @function_tool
        def get_weather(city: str):
            workflow.logger.debug(f"Getting weather for {city}")
            return f"The weather in {city} is sunny."

        agent = Agent(
            name="Assistant",
            instructions="You only respond in haikus. When asked about the weather always use the tool to get the current weather.",
            model=OPENROUTER_MODEL,
            tools=[get_weather],
        )

        result = await Runner.run(agent, prompt)
        return result.final_output
