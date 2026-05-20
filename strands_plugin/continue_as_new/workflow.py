"""Chat-style workflow that continues-as-new before history grows too large.

Each user turn arrives as a Temporal **update**, so the caller gets the
assistant's reply back from the same call. Once Temporal suggests
continue-as-new, the workflow drains any in-flight update handlers and hands
``agent.messages`` off to a fresh run.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import timedelta

from strands.types.content import Messages
from temporalio import workflow
from temporalio.contrib.strands import TemporalAgent


@dataclass
class ChatInput:
    messages: Messages = field(default_factory=list)


@workflow.defn
class ChatWorkflow:
    def __init__(self) -> None:
        self._done = False
        self._lock = asyncio.Lock()
        self._agent: TemporalAgent | None = None

    @workflow.update
    async def turn(self, prompt: str) -> str:
        # Updates can arrive before ``run`` has constructed the agent.
        await workflow.wait_condition(lambda: self._agent is not None)
        # Serialize turns so concurrent updates can't interleave on ``agent.messages``.
        async with self._lock:
            assert self._agent is not None
            result = await self._agent.invoke_async(prompt)
            return str(result).strip()

    @workflow.signal
    def end_chat(self) -> None:
        self._done = True

    @workflow.query
    def messages(self) -> Messages:
        return list(self._agent.messages) if self._agent else []

    @workflow.run
    async def run(self, input: ChatInput) -> None:
        self._agent = TemporalAgent(
            start_to_close_timeout=timedelta(seconds=60),
            messages=list(input.messages),
        )

        await workflow.wait_condition(
            lambda: self._done or workflow.info().is_continue_as_new_suggested()
        )

        # Let any in-flight ``turn`` updates finish before we exit or hand off.
        await workflow.wait_condition(workflow.all_handlers_finished)

        if not self._done:
            workflow.continue_as_new(ChatInput(messages=self._agent.messages))
