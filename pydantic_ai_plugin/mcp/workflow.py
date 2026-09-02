from dataclasses import dataclass

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from fastmcp import FastMCP
    from pydantic_ai import Agent
    from pydantic_ai.durable_exec.temporal import (
        PydanticAIWorkflow,
        TemporalDurability,
    )
    from pydantic_ai.mcp import MCPToolset
    from pydantic_ai.models.test import TestModel


@dataclass
class MCPInput:
    prompt: str
    model: str | None = None


server = FastMCP("support-directory")


@server.tool
def support_hours() -> str:
    return "Support is staffed 09:00-17:00 UTC."


toolset = MCPToolset(server, id="support_directory")
agent = Agent(
    TestModel(call_tools=["support_hours"], custom_output_text="Hours found."),
    name="mcp_support",
    toolsets=[toolset],
    capabilities=[TemporalDurability()],
)


@workflow.defn
class MCPWorkflow(PydanticAIWorkflow):
    __pydantic_ai_agents__ = [agent]

    @workflow.run
    async def run(self, input: MCPInput) -> str:
        result = await agent.run(input.prompt, model=input.model)
        return result.output
