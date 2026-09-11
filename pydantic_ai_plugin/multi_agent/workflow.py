from dataclasses import dataclass

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from pydantic_ai import Agent
    from pydantic_ai.durable_exec.temporal import (
        PydanticAIWorkflow,
        TemporalDurability,
    )
    from pydantic_ai.models.test import TestModel


@dataclass
class MultiAgentInput:
    topic: str
    model: str | None = None


researcher = Agent(
    TestModel(custom_output_text="Temporal records each completed step."),
    name="researcher",
    instructions="Find one accurate fact about the requested topic.",
    capabilities=[TemporalDurability()],
)
writer = Agent(
    TestModel(custom_output_text="A concise explanation is ready."),
    name="writer",
    instructions="Turn the supplied research into one concise sentence.",
    capabilities=[TemporalDurability()],
)


@workflow.defn
class MultiAgentWorkflow(PydanticAIWorkflow):
    __pydantic_ai_agents__ = [researcher, writer]

    @workflow.run
    async def run(self, input: MultiAgentInput) -> str:
        research = await researcher.run(input.topic, model=input.model)
        draft = await writer.run(
            f"Topic: {input.topic}\nResearch: {research.output}",
            model=input.model,
        )
        return draft.output
