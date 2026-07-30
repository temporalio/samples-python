from google.adk import Agent
from google.adk.runners import InMemoryRunner
from google.adk.utils.context_utils import Aclosing
from google.genai import types
from temporalio import workflow
from temporalio.contrib.google_adk_agents import TemporalModel


# @@@SNIPSTART google-adk-agents-basic-hello-world-agent-workflow
@workflow.defn
class HelloWorldAgentWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        # TemporalModel runs each model call as an `invoke_model` activity.
        agent = Agent(
            name="hello_world_agent",
            model=TemporalModel("gemini-2.5-flash"),
            instruction="You only respond in haikus.",
        )

        # The plugin points ADK's session-id generation at workflow.uuid4(), so
        # creating a session here is replay-safe.
        runner = InMemoryRunner(agent=agent, app_name="hello_world_app")
        session = await runner.session_service.create_session(
            app_name="hello_world_app", user_id="user"
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
