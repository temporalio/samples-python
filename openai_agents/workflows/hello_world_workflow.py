from temporalio import workflow


# Import our activity, passing it through the sandbox
# with workflow.unsafe.imports_passed_through():
from agents import Agent, Runner, RunConfig


@workflow.defn(sandboxed=False)
class HelloWorldAgent:
    @workflow.run
    async def run(self, prompt: str) -> str:
        agent = Agent(
            name="Assistant",
            instructions="You only respond in haikus.",
        )

        result = await Runner.run(agent, input=prompt)
        return result.final_output
