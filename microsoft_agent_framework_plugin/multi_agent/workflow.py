"""A coordinator agent that delegates to two sub-agents through ``Agent.as_tool()``.

Every agent runs in the Workflow and every agent's model calls run as
Activities, so the whole tree is durable with no per-agent wiring: to the
coordinator a sub-agent is a tool like any other.
"""

# @@@SNIPSTART python-microsoft-agent-framework-multi-agent-workflow
from datetime import timedelta

from agent_framework import Agent
from temporalio import workflow
from temporalio.microsoft_agent_framework import TemporalChatClient


def chat_client(summary: str) -> TemporalChatClient:
    # One client per agent, so each Activity's summary names the agent in the UI.
    return TemporalChatClient(
        "gpt-4o-mini", start_to_close_timeout=timedelta(seconds=60), summary=summary
    )


@workflow.defn
class MultiAgentWorkflow:
    @workflow.run
    async def run(self, topic: str) -> str:
        researcher = Agent(
            client=chat_client("researcher"),
            name="researcher",
            description="Lists three facts about a topic.",
            instructions="List three short facts about the topic you are given.",
        )
        writer = Agent(
            client=chat_client("writer"),
            name="writer",
            description="Writes one paragraph from a list of facts.",
            instructions="Write one short paragraph from the facts you are given.",
        )
        coordinator = Agent(
            client=chat_client("coordinator"),
            instructions=(
                "Ask the researcher for facts about the topic, then ask the writer "
                "to turn those facts into a paragraph. Reply with the paragraph."
            ),
            tools=[researcher.as_tool(), writer.as_tool()],
        )
        response = await coordinator.run(f"Write a paragraph about {topic}.")
        return response.text


# @@@SNIPEND
