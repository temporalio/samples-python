from __future__ import annotations

from datetime import timedelta

from agents import gen_trace_id, trace
from agents import Agent, Runner
from temporalio import workflow
from temporalio.contrib import openai_agents as temporal_agents

from openai_agents.workflows.get_weather_activity import get_weather


@workflow.defn
class ToolsWorkflow:
    @workflow.run
    async def run(self, question: str) -> str:
        trace_id = gen_trace_id()
        with trace("Activity as tool", trace_id=trace_id):
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
