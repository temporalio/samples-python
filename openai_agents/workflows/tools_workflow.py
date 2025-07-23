from __future__ import annotations

from datetime import timedelta

from agents import trace
from agents import Agent, Runner
from temporalio import workflow
from temporalio.contrib import openai_agents as temporal_agents

from openai_agents.workflows.get_weather_activity import get_weather


@workflow.defn
class ToolsWorkflow:
    @workflow.run
    async def run(self, question: str) -> str:
        with trace("Activity as tool"):
            agent = Agent(
                name="Hello world",
                instructions="You are a helpful agent.",
                tools=[
                    temporal_agents.workflow.activity_as_tool(
                        get_weather, start_to_close_timeout=timedelta(seconds=10)
                    )
                ],
            )

            result = await Runner.run(agent, input=question)
            return result.final_output
