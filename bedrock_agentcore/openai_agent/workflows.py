from datetime import timedelta

from temporalio import workflow
from temporalio.openai_agents.workflow import activity_as_tool

TASK_QUEUE = "agentcore-openai-task-queue"
DEPLOYMENT_NAME = "agentcore-openai-agent-python"
BUILD_ID = "1.0.0"

with workflow.unsafe.imports_passed_through():
    from agents import Agent, Runner

    from activities import execute_code

SYSTEM_PROMPT = """You are an AI assistant that validates answers through code execution.
When asked about code, algorithms, calculations, or data, write Python and run it with the
execute_code tool instead of working the answer out in your head. The sandbox persists
across calls, so variables you define in one call are still there in the next. Report both
the code you ran and its output."""


# @@@SNIPSTART python-agentcore-openai-workflow
@workflow.defn
class OpenAIAgentWorkflow:
    def __init__(self) -> None:
        # No model is named, so the Agents SDK's default OpenAI model is used
        # (override it with OPENAI_DEFAULT_MODEL on the Worker). Custom
        # instructions and the code interpreter tool.
        self.agent = Agent(
            name="Code Interpreter Assistant",
            instructions=SYSTEM_PROMPT,
            tools=[
                activity_as_tool(
                    execute_code,
                    start_to_close_timeout=timedelta(minutes=2),
                )
            ],
        )

    @workflow.run
    async def run(self, prompt: str) -> str:
        # The plugin runs each model call as an Activity; Runner.run is the
        # async entry point (Runner.run_sync would block the Workflow).
        result = await Runner.run(self.agent, prompt)
        return str(result.final_output)


# @@@SNIPEND
