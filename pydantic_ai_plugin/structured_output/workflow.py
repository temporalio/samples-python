from dataclasses import dataclass

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from pydantic import BaseModel, Field
    from pydantic_ai import Agent
    from pydantic_ai.durable_exec.temporal import (
        PydanticAIWorkflow,
        TemporalDurability,
    )
    from pydantic_ai.models.test import TestModel


class IncidentSummary(BaseModel):
    service: str = Field(description="Affected service")
    severity: int = Field(ge=1, le=5)
    action: str


@dataclass
class StructuredInput:
    prompt: str
    model: str | None = None


agent = Agent(
    TestModel(
        custom_output_args={
            "service": "payments",
            "severity": 2,
            "action": "Restart the worker pool.",
        }
    ),
    name="incident_structurer",
    output_type=IncidentSummary,
    capabilities=[TemporalDurability()],
)


@workflow.defn
class StructuredOutputWorkflow(PydanticAIWorkflow):
    __pydantic_ai_agents__ = [agent]

    @workflow.run
    async def run(self, input: StructuredInput) -> IncidentSummary:
        result = await agent.run(input.prompt, model=input.model)
        return result.output
