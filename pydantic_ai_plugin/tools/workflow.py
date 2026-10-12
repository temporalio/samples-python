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
class ToolsInput:
    prompt: str
    model: str | None = None


agent = Agent(
    TestModel(
        call_tools=["read_policy", "lookup_inventory"],
        custom_output_text="Both checks completed.",
    ),
    name="tool_boundaries",
    capabilities=[TemporalDurability()],
)


@agent.tool_plain(metadata={"temporal": False})
async def read_policy() -> str:
    return "policy: standard shipping"


@agent.tool_plain
async def lookup_inventory() -> str:
    return "inventory: 12 units"


@workflow.defn
class ToolsWorkflow(PydanticAIWorkflow):
    __pydantic_ai_agents__ = [agent]

    @workflow.run
    async def run(self, input: ToolsInput) -> str:
        result = await agent.run(input.prompt, model=input.model)
        return result.output
