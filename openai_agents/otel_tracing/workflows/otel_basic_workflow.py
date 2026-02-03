"""Basic OTEL tracing workflow demonstrating automatic instrumentation.

This workflow shows the simplest OTEL integration - just configure exporters in the
plugin and all agent/model/activity spans are automatically instrumented.
"""

from dataclasses import dataclass
from datetime import timedelta

from agents import Agent, Runner
from temporalio import activity, workflow
from temporalio.contrib import openai_agents as temporal_agents


@dataclass
class Weather:
    city: str
    temperature_range: str
    conditions: str


@activity.defn
async def get_weather(city: str) -> str:
    """Get the weather for a given city."""
    weather = Weather(
        city=city, temperature_range="14-20C", conditions="Sunny with wind."
    )
    return f"{weather.city}: {weather.conditions}, {weather.temperature_range}"


@workflow.defn
class OtelBasicWorkflow:
    """Workflow demonstrating automatic OTEL instrumentation.

    The OTEL integration automatically creates spans for:
    - Workflow execution
    - Agent runs
    - Model invocations (as activities)
    - Tool/activity calls

    No manual span creation needed!
    """

    @workflow.run
    async def run(self, question: str) -> str:
        agent = Agent(
            name="Weather Assistant",
            instructions="You are a helpful weather assistant.",
            tools=[
                temporal_agents.workflow.activity_as_tool(
                    get_weather, start_to_close_timeout=timedelta(seconds=10)
                )
            ],
        )

        # All spans are automatically created - no manual instrumentation required!
        result = await Runner.run(agent, input=question)
        return result.final_output
