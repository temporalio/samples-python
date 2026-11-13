"""A Workflow whose agent run is traced end to end."""

# @@@SNIPSTART python-agent-framework-open-telemetry-workflow
from datetime import timedelta

from agent_framework import Agent
from temporalio import workflow
from temporalio.agent_framework import TemporalChatClient


@workflow.defn
class TracedWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        agent = Agent(
            client=TemporalChatClient(
                "gpt-4o-mini", start_to_close_timeout=timedelta(seconds=60)
            ),
            # Agent Framework names its span after the agent: invoke_agent assistant.
            name="assistant",
            instructions="You are a concise assistant.",
        )
        response = await agent.run(prompt)
        return response.text


# @@@SNIPEND
