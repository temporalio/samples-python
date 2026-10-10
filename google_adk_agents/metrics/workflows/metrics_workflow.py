from google.adk import Agent
from google.adk.runners import InMemoryRunner
from google.adk.utils.context_utils import Aclosing
from google.genai import types
from temporalio import workflow
from temporalio.contrib.google_adk_agents import TemporalModel

from google_adk_agents.metrics.models.local_metrics_model import MODEL_NAME


@workflow.defn
class MetricsWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        agent = Agent(
            name="metrics_agent",
            model=TemporalModel(MODEL_NAME),
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
        return final_text
