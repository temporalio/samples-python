from temporalio import workflow

# Import agent Agent and Runner
with workflow.unsafe.imports_passed_through():
    from agents import Agent, Runner


@workflow.defn
class HelloWorldAgent:
    @workflow.run
    async def run(self, prompt: str) -> str:
        agent = Agent(
            name="Assistant",
            instructions="You only respond in haikus.",
        )

        result = await Runner.run(agent, input=prompt)
        return result.final_output
