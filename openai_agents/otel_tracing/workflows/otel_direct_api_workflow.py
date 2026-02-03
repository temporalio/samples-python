"""Direct OTEL API usage workflow demonstrating custom instrumentation.

This workflow shows how to use the OpenTelemetry API directly in workflows
to instrument custom business logic, add domain-specific spans, and set
custom attributes.

CRITICAL REQUIREMENTS:
1. Use trace() wrapper with custom_span() from Agents SDK to establish context
2. Wrap direct OTEL tracer calls in custom_span() (establishes OTEL bridge)
3. Configure sandbox passthrough for opentelemetry module in worker

Pattern: trace() -> custom_span() -> tracer.start_as_current_span()
"""

from dataclasses import dataclass
from datetime import timedelta

import opentelemetry.trace
from agents import Agent, Runner, custom_span, trace
from temporalio import activity, workflow
from temporalio.contrib import openai_agents as temporal_agents


@dataclass
class Weather:
    city: str
    temperature_range: str
    conditions: str
    air_quality: str = "Good"


@activity.defn
async def get_weather(city: str) -> str:
    """Get the weather for a given city."""
    weather = Weather(
        city=city,
        temperature_range="14-20C",
        conditions="Sunny with wind.",
        air_quality="Good",
    )
    return f"{weather.city}: {weather.conditions}, {weather.temperature_range}, Air Quality: {weather.air_quality}"


def validate_city_name(city: str) -> bool:
    """Validate that city name is reasonable."""
    # Simple validation logic
    return len(city) > 0 and len(city) < 100 and city.replace(" ", "").isalpha()


def calculate_travel_score(weather: str) -> int:
    """Calculate a travel score based on weather conditions."""
    # Simple scoring logic
    score = 50
    if "sunny" in weather.lower():
        score += 30
    if "wind" in weather.lower():
        score += 10
    if "good" in weather.lower():
        score += 10
    return score


@workflow.defn
class OtelDirectApiWorkflow:
    """Workflow demonstrating direct OTEL API usage for custom instrumentation.

    This workflow shows practical use cases for direct OTEL API:
    - Instrumenting business logic validation
    - Adding domain-specific spans with custom attributes
    - Setting custom attributes for observability
    - Creating detailed traces with business metrics

    IMPORTANT: When using direct OTEL API, wrap everything in trace() + custom_span():
    - trace() establishes the root trace context (required when using custom_span)
    - custom_span() bridges to OpenTelemetry context for direct tracer calls
    - Direct OTEL spans (tracer.start_as_current_span) go inside custom_span()
    """

    @workflow.run
    async def run(self, city: str) -> str:
        # trace() establishes the root context needed for custom_span() and direct OTEL API
        with trace("Travel recommendation workflow"):
            # custom_span() establishes OTEL context bridge for direct OTEL API calls
            with custom_span("Travel recommendation processing"):
                tracer = opentelemetry.trace.get_tracer(__name__)

                # Custom instrumentation: validate input
                with tracer.start_as_current_span("validate-input") as span:
                    span.set_attribute("input.city", city)
                    is_valid = validate_city_name(city)
                    span.set_attribute(
                        "validation.result", "valid" if is_valid else "invalid"
                    )

                    if not is_valid:
                        span.set_attribute("error", "Invalid city name")
                        return "Invalid city name provided"

                # Agent execution with automatic instrumentation
                agent = Agent(
                    name="Travel Weather Assistant",
                    instructions="You are a helpful travel weather assistant. Provide weather information in a friendly way.",
                    tools=[
                        temporal_agents.workflow.activity_as_tool(
                            get_weather, start_to_close_timeout=timedelta(seconds=10)
                        )
                    ],
                )

                with tracer.start_as_current_span("fetch-weather-info") as span:
                    span.set_attribute("request.city", city)
                    result = await Runner.run(
                        agent, input=f"What's the weather like in {city}?"
                    )
                    weather_info = result.final_output
                    span.set_attribute("response.length", len(weather_info))

                # Custom instrumentation: calculate business metric
                with tracer.start_as_current_span("calculate-travel-score") as span:
                    span.set_attribute("city", city)
                    travel_score = calculate_travel_score(weather_info)
                    span.set_attribute("travel.score", travel_score)
                    span.set_attribute(
                        "travel.recommendation",
                        "recommended" if travel_score > 70 else "not_recommended",
                    )

                # Custom instrumentation: format final response
                with tracer.start_as_current_span("format-response") as span:
                    span.set_attribute("include.score", True)
                    final_response = (
                        f"{weather_info}\n\nTravel Score: {travel_score}/100"
                    )
                    span.set_attribute("response.final_length", len(final_response))

                return final_response
