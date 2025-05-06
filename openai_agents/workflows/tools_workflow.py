from __future__ import annotations

from temporalio import workflow

# Import our activity, passing it through the sandbox
with workflow.unsafe.imports_passed_through():
    from agents import Agent, Runner, RunConfig
    from openai_agents.adapters.activity_model import ModelStubProvider, activity_as_tool
    from openai_agents.workflows.get_weather_activity import get_weather


@workflow.defn(sandboxed=False)
class ToolsWorkflow:
    @workflow.run
    async def run(self, question: str) -> str:
        agent = Agent(
            name="Hello world",
            instructions="You are a helpful agent.",
            tools=[activity_as_tool(get_weather)],
        )

        config = RunConfig(model_provider=ModelStubProvider())
        result = await Runner.run(agent, input=question, run_config=config)
        return result.final_output
