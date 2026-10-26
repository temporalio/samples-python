from __future__ import annotations

from dataclasses import dataclass

from agents import Agent, Runner, function_tool
from temporalio import workflow


# @@@SNIPSTART python-openai-agents-openai-compatible-workflow
@dataclass
class OpenAICompatibleAgentInput:
    prompt: str
    # "<provider>/<model>", such as "together/openai/gpt-oss-120b". The Worker's
    # model provider routes the agent's model calls to that provider.
    model: str


@workflow.defn
class OpenAICompatibleAgentWorkflow:
    @workflow.run
    async def run(self, input: OpenAICompatibleAgentInput) -> str:
        # Tools that run inside the Workflow must be async: the Agents SDK runs
        # sync tools in a thread, which the Workflow sandbox does not allow.
        @function_tool
        async def get_weather(city: str) -> str:
            workflow.logger.debug(f"Getting weather for {city}")
            return f"The weather in {city} is sunny."

        agent = Agent(
            name="Assistant",
            instructions="You only respond in haikus. When asked about the weather always use the tool to get the current weather.",
            model=input.model,
            tools=[get_weather],
        )

        result = await Runner.run(agent, input.prompt)
        return result.final_output


# @@@SNIPEND
