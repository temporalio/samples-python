from __future__ import annotations

from agents import Agent, ModelSettings, Runner, function_tool
from temporalio import workflow


# @@@SNIPSTART python-openai-agents-openai-compatible-workflow
@workflow.defn
class OpenAICompatibleAgentWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        # Tools that run inside the Workflow must be async: the Agents SDK runs
        # sync tools in a thread, which the Workflow sandbox does not allow.
        @function_tool
        async def get_weather(city: str) -> str:
            workflow.logger.debug(f"Getting weather for {city}")
            return f"The weather in {city} is sunny."

        # No model is named here, so the Worker's model provider supplies its
        # default. Set model= to any model the provider serves to override it.
        # Start from empty model settings: an agent that names no model gets
        # the Agents SDK's defaults for OpenAI's default model (a reasoning
        # effort and `verbosity`), which other providers reject.
        agent = Agent(
            name="Assistant",
            instructions="You only respond in haikus. When asked about the weather always use the tool to get the current weather.",
            model_settings=ModelSettings(),
            tools=[get_weather],
        )

        result = await Runner.run(agent, prompt)
        return result.final_output


# @@@SNIPEND
