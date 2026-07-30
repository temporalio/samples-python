from __future__ import annotations

from agents import Agent, Runner, WebSearchTool
from temporalio import workflow


@workflow.defn
class WebSearchWorkflow:
    @workflow.run
    async def run(self, question: str, user_city: str = "New York") -> str:
        agent = Agent(
            name="Web searcher",
            instructions="You are a helpful agent.",
            tools=[
                WebSearchTool(user_location={"type": "approximate", "city": user_city})
            ],
        )

        result = await Runner.run(agent, question)
        return result.final_output
