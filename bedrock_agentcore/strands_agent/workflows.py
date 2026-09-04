from datetime import timedelta

from temporalio import workflow
from temporalio.contrib.strands import TemporalAgent
from temporalio.contrib.strands.workflow import activity_as_tool

TASK_QUEUE = "agentcore-strands-task-queue"
DEPLOYMENT_NAME = "agentcore-strands-agent-python"
BUILD_ID = "1.0.0"

with workflow.unsafe.imports_passed_through():
    from activities import execute_code

SYSTEM_PROMPT = """You are an AI assistant that validates answers through code execution.
When asked about code, algorithms, calculations, or data, write Python and run it with the
execute_code tool instead of working the answer out in your head. The sandbox persists
across calls, so variables you define in one call are still there in the next. Report both
the code you ran and its output."""


@workflow.defn
class StrandsAgentWorkflow:
    def __init__(self) -> None:
        # Configure with the plugin's default BedrockModel(), custom system
        # prompt and code interpreter tool.
        self.agent = TemporalAgent(
            start_to_close_timeout=timedelta(seconds=60),
            system_prompt=SYSTEM_PROMPT,
            tools=[
                activity_as_tool(
                    execute_code,
                    start_to_close_timeout=timedelta(minutes=2),
                )
            ],
        )

    @workflow.run
    async def run(self, prompt: str) -> str:
        # invoke_async, not agent(prompt) -- the sync form spawns a worker thread the
        # Workflow sandbox blocks.
        result = await self.agent.invoke_async(prompt)
        return str(result)
