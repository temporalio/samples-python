from agents import Agent, Runner
from agents import gen_trace_id, trace
from temporalio import workflow


@workflow.defn
class HelloWorldAgent:
    @workflow.run
    async def run(self, prompt: str) -> str:
        trace_id = gen_trace_id()
        with trace("Hello World", trace_id=trace_id):
            agent = Agent(
                name="Assistant",
                instructions="You only respond in haikus.",
            )

            result = await Runner.run(agent, input=prompt)
            return result.final_output
