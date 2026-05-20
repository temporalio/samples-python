"""Chat-style workflow that continues-as-new before history grows too large.

Every turn appends to ``agent.messages``. Once Temporal suggests
continue-as-new, the workflow hands the accumulated messages off to a fresh
run, which seeds a new ``TemporalAgent`` with them and keeps the chat going.
"""

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
        self._pending: list[str] = []
        self._done = False
        self._messages: Messages = []

    @workflow.signal
    def user_says(self, prompt: str) -> None:
        self._pending.append(prompt)

    @workflow.signal
    def end_chat(self) -> None:
        self._done = True

    @workflow.query
    def messages(self) -> Messages:
        return list(self._messages)

    @workflow.run
    async def run(self, input: ChatInput) -> None:
        agent = TemporalAgent(
            start_to_close_timeout=timedelta(seconds=60),
            messages=list(input.messages),
        )
        self._messages = agent.messages

        while True:
            await workflow.wait_condition(lambda: bool(self._pending) or self._done)
            if self._done:
                return
            prompt = self._pending.pop(0)
            await agent.invoke_async(prompt)
            self._messages = agent.messages
            if workflow.info().is_continue_as_new_suggested():
                workflow.continue_as_new(ChatInput(messages=agent.messages))
