# @@@SNIPSTART python-openai-agents-hello-world-workflow
from agents import Agent, Runner
from temporalio import workflow


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


# @@@SNIPEND
