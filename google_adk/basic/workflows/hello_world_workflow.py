from __future__ import annotations

from contextlib import aclosing

from temporalio import workflow
from temporalio.contrib.google_adk_agents import TemporalModel

with workflow.unsafe.imports_passed_through():
    from google.adk.agents import Agent
    from google.adk.runners import InMemoryRunner
    from google.genai import types


@workflow.defn
class HelloWorldWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        agent = Agent(
            name="Assistant",
            model=TemporalModel("gemini-2.5-flash"),
            instruction="You only respond in haikus.",
        )

        runner = InMemoryRunner(agent=agent, app_name="hello_world")
        session = await runner.session_service.create_session(
            user_id="user", app_name="hello_world"
        )

        result = ""
        async with aclosing(
            runner.run_async(
                user_id="user",
                session_id=session.id,
                new_message=types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=prompt)],
                ),
            )
        ) as events:
            async for event in events:
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            result = part.text

        return result
