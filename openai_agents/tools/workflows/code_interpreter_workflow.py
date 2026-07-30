from __future__ import annotations

from agents import Agent, CodeInterpreterTool, Runner
from temporalio import workflow


@workflow.defn
class CodeInterpreterWorkflow:
    @workflow.run
    async def run(self, question: str) -> str:
        agent = Agent(
            name="Code interpreter",
            instructions="You love doing math.",
            tools=[
                CodeInterpreterTool(
                    tool_config={
                        "type": "code_interpreter",
                        "container": {"type": "auto"},
                    },
                )
            ],
        )

        result = await Runner.run(agent, question)
        return result.final_output
