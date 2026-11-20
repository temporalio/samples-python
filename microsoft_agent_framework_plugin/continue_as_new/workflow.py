"""A chat that continues as new before its history grows too large.

Each user turn is an Update, so the caller gets the reply from the same call.
When Temporal suggests Continue-As-New, the Workflow lets in-flight Updates
finish and hands the serialized session to a fresh run. ``session.to_dict()``
carries the transcript and Agent Framework's own session state across the
boundary; the ``Agent`` object does not cross and is built again in the new run.
Nothing waits in Workflow fields at the handoff: a ``turn`` is an Update, so it
completes in the run that accepted it, ``workflow.all_handlers_finished`` lets
an accepted turn finish before the handoff, and an ``end_chat`` that arrives
during a turn ends the chat after that turn.
"""

# @@@SNIPSTART python-microsoft-agent-framework-continue-as-new-workflow
import asyncio
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from agent_framework import Agent, AgentSession, InMemoryHistoryProvider
from temporalio import workflow
from temporalio.microsoft_agent_framework import TemporalChatClient


@dataclass
class ChatInput:
    session: dict[str, Any] | None = None


@workflow.defn
class ChatWorkflow:
    @workflow.init
    def __init__(self, input: ChatInput) -> None:
        # Runs before any handler, so a turn that arrives with the start finds
        # the agent and the session ready.
        self._done = False
        self._lock = asyncio.Lock()
        self._agent = Agent(
            client=TemporalChatClient(
                "gpt-4o-mini", start_to_close_timeout=timedelta(seconds=60)
            ),
            instructions="You are a helpful assistant. Keep replies short.",
        )
        self._session = (
            AgentSession.from_dict(input.session)
            if input.session
            else self._agent.create_session()
        )

    @workflow.update
    async def turn(self, prompt: str) -> str:
        # One turn at a time, so the session's history stays in order.
        async with self._lock:
            response = await self._agent.run(prompt, session=self._session)
            return response.text

    @workflow.signal
    def end_chat(self) -> None:
        self._done = True

    @workflow.query
    def transcript(self) -> list[dict[str, str]]:
        # Agent Framework's in-memory history provider keeps the messages here.
        state = self._session.state.get(InMemoryHistoryProvider.DEFAULT_SOURCE_ID, {})
        messages = state.get("messages", [])
        return [
            {
                "role": str(getattr(message.role, "value", message.role)),
                "text": message.text,
            }
            for message in messages
        ]

    @workflow.run
    async def run(self, input: ChatInput) -> None:
        await workflow.wait_condition(
            lambda: self._done or workflow.info().is_continue_as_new_suggested()
        )
        # Let in-flight turns finish before the handoff.
        await workflow.wait_condition(workflow.all_handlers_finished)

        if not self._done:
            workflow.continue_as_new(ChatInput(session=self._session.to_dict()))


# @@@SNIPEND
