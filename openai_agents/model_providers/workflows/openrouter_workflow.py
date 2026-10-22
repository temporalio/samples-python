from __future__ import annotations

from agents import Agent, Runner, function_tool
from temporalio import workflow

# OpenRouter's Auto Router picks a model per request and takes tool support
# into account. Any OpenRouter model slug works here instead.
OPENROUTER_MODEL = "openrouter/auto"


@workflow.defn
class OpenRouterAgentWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        # Tools that run inside the Workflow must be async: the Agents SDK runs
        # sync tools in a thread, which the Workflow sandbox does not allow.
        @function_tool
        async def get_weather(city: str) -> str:
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
