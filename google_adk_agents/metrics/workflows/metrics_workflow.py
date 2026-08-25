from datetime import timedelta

from google.adk import Agent
from google.adk.runners import InMemoryRunner
from google.adk.utils.context_utils import Aclosing
from google.genai import types
from temporalio import workflow
from temporalio.contrib.google_adk_agents import TemporalModel


@workflow.defn
class MetricsWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        agent = Agent(
            name="metrics_agent",
            model=TemporalModel("local-metrics-model"),
            instruction="Answer the user briefly.",
        )
        runner = InMemoryRunner(agent=agent, app_name="metrics_app")
        session = await runner.session_service.create_session(
            app_name="metrics_app", user_id="sample-user"
        )

        final_text = ""
        async with Aclosing(
            runner.run_async(
                user_id="sample-user",
                session_id=session.id,
                new_message=types.Content(role="user", parts=[types.Part(text=prompt)]),
            )
        ) as events:
            async for event in events:
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            final_text = part.text
        await workflow.sleep(timedelta(milliseconds=1))
        return final_text
