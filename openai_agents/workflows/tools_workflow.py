from __future__ import annotations

from datetime import timedelta

from agents import gen_trace_id
from temporalio import workflow
from temporalio.contrib.openai_agents.temporal_tools import activity_as_tool

# Import our activity, passing it through the sandbox
with workflow.unsafe.imports_passed_through():
    from agents import Agent, Runner, trace

    from openai_agents.workflows.get_weather_activity import get_weather


@workflow.defn
class ToolsWorkflow:
    @workflow.run
    async def run(self, question: str) -> str:
        trace_id = gen_trace_id()
        with trace("Activity as tool", trace_id=trace_id):
            agent = Agent(
                name="Weather agent",
                instructions="You are a helpful agent.",
                tools=[
                    activity_as_tool(
                        get_weather, start_to_close_timeout=timedelta(seconds=10)
                    )
                ],
            )

            result = await Runner.run(agent, input=question)
            return result.final_output
