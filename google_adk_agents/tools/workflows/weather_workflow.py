from datetime import timedelta

import temporalio.contrib.google_adk_agents.workflow
from google.adk import Agent
from google.adk.runners import InMemoryRunner
from google.adk.utils.context_utils import Aclosing
from google.genai import types
from temporalio import workflow
from temporalio.contrib.google_adk_agents import TemporalModel

from google_adk_agents.tools.activities.weather_activity import get_weather


# @@@SNIPSTART google-adk-agents-tools-weather-agent-workflow
@workflow.defn
class WeatherAgentWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        # Wrap the get_weather activity as an ADK tool. When the model calls it,
        # activity_tool runs it as a real Temporal activity instead of inline,
        # so it's retryable and shows up in history.
        weather_tool = temporalio.contrib.google_adk_agents.workflow.activity_tool(
            get_weather, start_to_close_timeout=timedelta(seconds=60)
        )

        agent = Agent(
            name="weather_agent",
            model=TemporalModel("gemini-2.5-flash"),
            instruction="Use the get_weather tool to answer weather questions.",
            tools=[weather_tool],
        )

        runner = InMemoryRunner(agent=agent, app_name="weather_app")
        session = await runner.session_service.create_session(
            app_name="weather_app", user_id="user"
        )

        final_text = ""
        async with Aclosing(
            runner.run_async(
                user_id="user",
                session_id=session.id,
                new_message=types.Content(role="user", parts=[types.Part(text=prompt)]),
            )
        ) as agen:
            async for event in agen:
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            final_text = part.text

        return final_text


# @@@SNIPEND
