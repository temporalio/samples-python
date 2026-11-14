"""One Agent Framework agent, one prompt, one model Activity."""

# @@@SNIPSTART python-microsoft-agent-framework-hello-world-workflow
from datetime import timedelta

from agent_framework import Agent
from temporalio import workflow
from temporalio.microsoft_agent_framework import TemporalChatClient


@workflow.defn
class HelloWorldWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        agent = Agent(
            client=TemporalChatClient(
                "gpt-4o-mini", start_to_close_timeout=timedelta(seconds=60)
            ),
            instructions="You are a concise assistant.",
        )
        response = await agent.run(prompt)
        return response.text


# @@@SNIPEND
