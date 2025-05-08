from temporalio import workflow

from openai_agents.adapters.temporal_model_provider import TemporalModelProvider

# Import our activity, passing it through the sandbox
with workflow.unsafe.imports_passed_through():
    from agents import Agent, Runner, RunConfig


@workflow.defn(sandboxed=False)
class HelloWorldAgent:
    @workflow.run
    async def run(self, prompt: str) -> str:
        agent = Agent(
            name="Assistant",
            instructions="You only respond in haikus.",
        )
        config = RunConfig(model_provider=TemporalModelProvider())
        result = await Runner.run(agent, input=prompt, run_config=config)
        return result.final_output
