"""Minimal Temporal + Strands workflow: one agent, one prompt."""

# @@@SNIPSTART python-strands-hello-world-workflow
from datetime import timedelta

from temporalio import workflow
from temporalio.contrib.strands import TemporalAgent


@workflow.defn
class HelloWorldWorkflow:
    def __init__(self) -> None:
        self.agent = TemporalAgent(start_to_close_timeout=timedelta(seconds=60))

    @workflow.run
    async def run(self, prompt: str) -> str:
        result = await self.agent.invoke_async(prompt)
        return str(result)
# @@@SNIPEND
