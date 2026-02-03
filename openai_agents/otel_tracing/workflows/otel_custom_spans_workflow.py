"""Custom spans workflow demonstrating logical grouping with trace() + custom_span().

This workflow shows how to use trace() wrapper with custom_span() to create logical
groupings of related operations, while still benefiting from automatic instrumentation
of agent/model/activity calls.

IMPORTANT: When using custom_span(), wrap it with trace() in the workflow (not client).
"""

from dataclasses import dataclass
from datetime import timedelta

from agents import Agent, Runner, custom_span, trace
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
class OtelCustomSpansWorkflow:
    """Workflow demonstrating custom spans for logical grouping.

    This example shows how to use trace() + custom_span() to create logical
    groupings of related operations. This pattern is useful when you want to:
    - Group related operations under a single span
    - Add meaningful structure to your traces
    - Keep instrumentation simple while adding context

    IMPORTANT: When using custom_span(), you must wrap it with trace() in the
    workflow to establish proper trace context. Never use trace() in client code.

    The OTEL integration still automatically creates spans for:
    - Workflow execution
    - Agent runs
    - Model invocations (as activities)
    - Tool/activity calls
    """

    @workflow.run
    async def run(self) -> str:
        with trace("Custom span sample"):
            agent = Agent(
                name="Weather Assistant",
                instructions="You are a helpful weather assistant. Be concise.",
                tools=[
                    temporal_agents.workflow.activity_as_tool(
                        get_weather, start_to_close_timeout=timedelta(seconds=10)
                    )
                ],
            )

            # Use custom_span to group multiple related agent calls under one logical operation
            # This makes it easy to see all weather checks for this request in your trace
            with custom_span("Multi-city weather check"):
                cities = ["Tokyo", "Paris", "New York"]
                results = []
                for city in cities:
                    result = await Runner.run(
                        agent, input=f"What's the weather in {city}?"
                    )
                    results.append(f"{city}: {result.final_output}")

                return "\n\n".join(results)
