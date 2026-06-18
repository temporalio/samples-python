"""Two tool surfaces on one Gemini call, both driven by automatic function calling.

1. ``@activity.defn get_weather`` wrapped via ``activity_as_tool`` — runs as a
   durable Temporal activity. Use this for I/O or non-deterministic work.
2. ``recommend_activity`` — a plain workflow method passed directly as a tool.
   It runs deterministically in-workflow with no activity dispatch.

Gemini's automatic function-calling (AFC) loop runs inside the workflow and
invokes both as needed.
"""

from datetime import timedelta

from google.genai import types
from temporalio import activity, workflow
from temporalio.contrib.google_genai import TemporalAsyncClient, activity_as_tool
from temporalio.workflow import ActivityConfig


@activity.defn
async def get_weather(city: str) -> str:
    """Look up the current weather for a city."""
    # Stub — replace with a real HTTP call in production.
    return f"It's 72F and sunny in {city}."


@workflow.defn
class ToolsWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        client = TemporalAsyncClient()
        response = await client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[
                    activity_as_tool(
                        get_weather,
                        activity_config=ActivityConfig(
                            start_to_close_timeout=timedelta(seconds=30),
                        ),
                    ),
                    self.recommend_activity,
                ],
            ),
        )
        return response.text or ""

    async def recommend_activity(self, weather: str) -> str:
        """Recommend something to do given a weather description."""
        if "sunny" in weather.lower():
            return "Go for a hike."
        return "Visit a museum."
