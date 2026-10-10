import asyncio
from dataclasses import dataclass, field

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from pydantic_ai import Agent, ModelMessage
    from pydantic_ai.durable_exec.temporal import (
        PydanticAIWorkflow,
        TemporalDurability,
    )
    from pydantic_ai.models.test import TestModel


@dataclass
class ChatInput:
    messages: list[ModelMessage] = field(default_factory=list)
    model: str | None = None


agent = Agent(
    TestModel(custom_output_text="Ready for the next turn."),
    name="durable_chat",
    capabilities=[TemporalDurability()],
)


@workflow.defn
class ChatWorkflow(PydanticAIWorkflow):
    __pydantic_ai_agents__ = [agent]

    @workflow.init
    def __init__(self, input: ChatInput) -> None:
        self._input = input
        self._messages = list(input.messages)
        self._done = False
        self._lock = asyncio.Lock()

    @workflow.update
    async def turn(self, prompt: str) -> str:
        async with self._lock:
            result = await agent.run(
                prompt,
                message_history=self._messages,
                model=self._input.model,
            )
            self._messages = result.all_messages()
            return result.output

    @workflow.signal
    def end_chat(self) -> None:
        self._done = True

    @workflow.query
    def message_count(self) -> int:
        return len(self._messages)

    @workflow.run
    async def run(self, input: ChatInput) -> None:
        await workflow.wait_condition(
            lambda: self._done or workflow.info().is_continue_as_new_suggested()
        )
        await workflow.wait_condition(workflow.all_handlers_finished)
        if not self._done:
            workflow.continue_as_new(
                ChatInput(messages=self._messages, model=input.model)
            )
