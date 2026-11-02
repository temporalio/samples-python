import uuid
from typing import Any

from temporalio.claude_agent_sdk import ClaudeAgentSDKPlugin
from temporalio.client import Client
from temporalio.worker import Replayer, Worker

from claude_agent_sdk_plugin.multi_agent.run_worker import (
    BRIEFING,
    OFFLINE_ANSWERS,
    RESEARCH_NOTES,
)
from claude_agent_sdk_plugin.multi_agent.workflow import MultiAgentWorkflow
from claude_agent_sdk_plugin.offline import scripted_api


def system_of(request: dict[str, Any]) -> str:
    return " ".join(block["text"] for block in request["system"])


async def test_coordinator_delegates_to_both_subagents(client: Client) -> None:
    with scripted_api(OFFLINE_ANSWERS) as api:
        async with Worker(
            client,
            task_queue=f"claude-agent-sdk-multi-agent-{uuid.uuid4()}",
            workflows=[MultiAgentWorkflow],
            plugins=[ClaudeAgentSDKPlugin()],
        ) as worker:
            handle = await client.start_workflow(
                MultiAgentWorkflow.run,
                "durable execution",
                id=f"claude-agent-sdk-multi-agent-{uuid.uuid4()}",
                task_queue=worker.task_queue,
            )
            briefing = await handle.result()

    assert briefing.result == f"Final briefing: {BRIEFING}"
    assert briefing.messages_by_agent["researcher"] == [RESEARCH_NOTES]
    assert briefing.messages_by_agent["writer"] == [BRIEFING]
    assert briefing.messages_by_agent["coordinator"][-1] == briefing.result

    assert api.asked == [
        "short briefing on this topic",
        "Collect three key facts",
        "tool_result:toolu_research",
        "Turn these notes",
        "tool_result:toolu_write",
    ]
    assert len([r for r in api.requests if "You are a researcher" in system_of(r)]) == 1
    assert len([r for r in api.requests if "You are a writer" in system_of(r)]) == 1

    await Replayer(
        workflows=[MultiAgentWorkflow], plugins=[ClaudeAgentSDKPlugin()]
    ).replay_workflow(await handle.fetch_history())
