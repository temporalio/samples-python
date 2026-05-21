from __future__ import annotations

from agents import Agent, Runner, function_tool
from temporalio import workflow


@workflow.defn
class TuningEnginesWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        @function_tool
        def summarize_gateway_policy(topic: str):
            return (
                f"For {topic}, keep model access scoped, log usage, and route "
                "through approved tenant model aliases."
            )

        agent = Agent(
            name="Assistant",
            instructions=(
                "You explain production AI gateway tradeoffs clearly and use the "
                "policy summary tool when governance is relevant."
            ),
            model="tuning-engines-default",
            tools=[summarize_gateway_policy],
        )

        result = await Runner.run(agent, prompt)
        return result.final_output
