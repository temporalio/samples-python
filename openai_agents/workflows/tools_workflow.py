from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.contrib import openai_agents

# Import our activity, passing it through the sandbox
with workflow.unsafe.imports_passed_through():
    from agents import Agent, Runner

    from openai_agents.workflows.get_weather_activity import get_weather


@workflow.defn
class ToolsWorkflow:
    @workflow.run
    async def run(self, question: str) -> str:
        agent = Agent(
            name="Hello world",
            instructions="You are a helpful agent.",
            tools=[
                openai_agents.workflow.activity_as_tool(
                    get_weather, start_to_close_timeout=timedelta(seconds=10)
                )
            ],
        )

        result = await Runner.run(agent, input=question)
        return result.final_output
