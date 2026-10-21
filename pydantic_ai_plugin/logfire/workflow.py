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
class ObservabilityInput:
    prompt: str
    model: str | None = None


agent = Agent(
    TestModel(custom_output_text="This run is traced."),
    name="observable_agent",
    capabilities=[TemporalDurability()],
)


@workflow.defn
class ObservabilityWorkflow(PydanticAIWorkflow):
    __pydantic_ai_agents__ = [agent]

    @workflow.run
    async def run(self, input: ObservabilityInput) -> str:
        result = await agent.run(input.prompt, model=input.model)
        return result.output
