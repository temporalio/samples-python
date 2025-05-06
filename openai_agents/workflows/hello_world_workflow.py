from temporalio import workflow


# Import our activity, passing it through the sandbox
with workflow.unsafe.imports_passed_through():
    from agents import Agent, Runner, RunConfig
    from openai_agents.adapters.activity_model import ModelStubProvider


@workflow.defn(sandboxed=False)
class HelloWorldAgent:
    @workflow.run
    async def run(self, prompt: str) -> str:
        agent = Agent(
            name="Assistant",
            instructions="You only respond in haikus.",
        )
        config = RunConfig(model_provider=ModelStubProvider())
        result = await Runner.run(agent, input=prompt, run_config=config)
        return result.final_output
