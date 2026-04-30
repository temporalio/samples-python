from __future__ import annotations

from contextlib import aclosing
from datetime import timedelta

from temporalio import workflow
from temporalio.contrib.google_adk_agents import TemporalModel
from temporalio.contrib.google_adk_agents.workflow import activity_tool

with workflow.unsafe.imports_passed_through():
    from google.adk.agents import Agent
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    from google_adk.basic.activities.get_weather_activity import get_weather
    from google_adk.basic.activities.search_web_activity import search_web


@workflow.defn
class ToolsWorkflow:
    @workflow.run
    async def run(self, question: str) -> str:
        weather_tool = activity_tool(
            get_weather, start_to_close_timeout=timedelta(seconds=10)
        )
        search_tool = activity_tool(
            search_web, start_to_close_timeout=timedelta(seconds=10)
        )

        agent = Agent(
            name="ToolsAgent",
            model=TemporalModel("gemini-2.5-flash"),
            instruction="You are a helpful agent. Use tools to answer questions.",
            tools=[weather_tool, search_tool],
        )

        runner = InMemoryRunner(agent=agent, app_name="tools_agent")
        session = await runner.session_service.create_session(
            user_id="user", app_name="tools_agent"
        )

        result = ""
        async with aclosing(
            runner.run_async(
                user_id="user",
                session_id=session.id,
                new_message=types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=question)],
                ),
            )
        ) as events:
            async for event in events:
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            result = part.text

        return result
