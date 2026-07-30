import asyncio

from google.adk import Agent
from google.adk.runners import InMemoryRunner
from google.adk.utils.context_utils import Aclosing
from google.genai import types
from temporalio import workflow
from temporalio.contrib.google_adk_agents import TemporalModel


# @@@SNIPSTART google-adk-agents-chatbot-agent-workflow
@workflow.defn
class ChatbotAgentWorkflow:
    def __init__(self) -> None:
        self._ready = False
        self._runner: InMemoryRunner | None = None
        self._session_id: str | None = None

    @workflow.run
    async def run(self) -> str:
        agent = Agent(
            name="chatbot_agent",
            model=TemporalModel("gemini-2.5-flash"),
            instruction="You are a helpful assistant.",
        )

        # The plugin points ADK's session-id generation at workflow.uuid4(), so
        # creating a session here is replay-safe.
        self._runner = InMemoryRunner(agent=agent, app_name="chatbot_app")
        session = await self._runner.session_service.create_session(
            app_name="chatbot_app", user_id="user"
        )
        self._session_id = session.id
        self._ready = True

        # Block forever to stay alive serving update turns; the client
        # terminates the workflow when the user quits.
        return await asyncio.Future()

    @workflow.update
    async def message(self, message: str) -> str:
        # An update can arrive before run() has created the runner and session,
        # so wait until they are ready before using them.
        await workflow.wait_condition(lambda: self._ready)
        assert self._runner is not None and self._session_id is not None

        final_text = ""
        async with Aclosing(
            self._runner.run_async(
                user_id="user",
                session_id=self._session_id,
                new_message=types.Content(
                    role="user", parts=[types.Part(text=message)]
                ),
            )
        ) as event_stream:
            async for event in event_stream:
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            final_text = part.text

        return final_text

    @message.validator
    def validate_message(self, message: str) -> None:
        # Verify user messages here
        pass


# @@@SNIPEND
