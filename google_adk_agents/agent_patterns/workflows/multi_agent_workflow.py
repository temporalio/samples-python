from datetime import timedelta

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from temporalio import workflow
from temporalio.contrib.google_adk_agents import TemporalModel
from temporalio.workflow import ActivityConfig


# @@@SNIPSTART google-adk-agents-agent-patterns-multi-agent-workflow
@workflow.defn
class MultiAgentWorkflow:
    @workflow.run
    async def run(self, topic: str) -> str:
        session_service = InMemorySessionService()
        session = await session_service.create_session(
            app_name="multi_agent_app", user_id="user"
        )

        # Each sub-agent gets its own TemporalModel with an ActivityConfig
        # summary, so its model turns show up as named activities in history.
        researcher = LlmAgent(
            name="researcher",
            model=TemporalModel(
                "gemini-2.5-flash",
                activity_config=ActivityConfig(summary="Researcher Agent"),
            ),
            instruction="You are a researcher. Find information about the topic.",
        )

        writer = LlmAgent(
            name="writer",
            model=TemporalModel(
                "gemini-2.5-flash",
                activity_config=ActivityConfig(summary="Writer Agent"),
            ),
            instruction="You are a poet. Write a haiku based on the research.",
        )

        # The coordinator delegates to the sub-agents via ADK's built-in
        # transfer_to_agent handoff, which runs durably here.
        coordinator = LlmAgent(
            name="coordinator",
            model=TemporalModel(
                "gemini-2.5-flash",
                activity_config=ActivityConfig(
                    start_to_close_timeout=timedelta(seconds=30),
                    summary="Coordinator Agent",
                ),
            ),
            instruction="You are a coordinator. Delegate to researcher then writer.",
            sub_agents=[researcher, writer],
        )

        runner = Runner(
            agent=coordinator,
            app_name="multi_agent_app",
            session_service=session_service,
        )

        final_text = ""
        user_msg = types.Content(
            role="user",
            parts=[
                types.Part(
                    text=f"Write a haiku about {topic}. First research it, then write it."
                )
            ],
        )
        async for event in runner.run_async(
            user_id="user", session_id=session.id, new_message=user_msg
        ):
            if event.content and event.content.parts and event.content.parts[0].text:
                final_text = event.content.parts[0].text

        return final_text


# @@@SNIPEND
