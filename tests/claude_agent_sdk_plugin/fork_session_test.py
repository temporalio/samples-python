import json
import uuid
from typing import Any

from temporalio.claude_agent_sdk import ClaudeAgentSDKPlugin
from temporalio.client import Client
from temporalio.worker import Replayer, Worker

from claude_agent_sdk_plugin.fork_session.run_worker import OFFLINE_ANSWERS
from claude_agent_sdk_plugin.fork_session.workflow import ForkSessionWorkflow
from claude_agent_sdk_plugin.offline import prompt_of, scripted_api

PROMPT = "Plan a weekend in Lisbon"
FOLLOW_UPS = ["Redo it on a tight budget.", "Redo it with no budget limit."]


async def test_each_follow_up_runs_in_its_own_fork_of_the_conversation(
    client: Client,
) -> None:
    task_queue = f"claude-agent-sdk-fork-session-{uuid.uuid4()}"
    with scripted_api(OFFLINE_ANSWERS) as api:
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[ForkSessionWorkflow],
            plugins=[ClaudeAgentSDKPlugin()],
        ):
            handle = await client.start_workflow(
                ForkSessionWorkflow.run,
                args=[PROMPT, FOLLOW_UPS],
                id=f"fork-session-{uuid.uuid4()}",
                task_queue=task_queue,
            )
            budget, luxury = await handle.result()

    assert budget.answer == OFFLINE_ANSWERS["on a tight budget"]
    assert luxury.answer == OFFLINE_ANSWERS["with no budget limit"]
    assert budget.session_id != luxury.session_id

    # Each fork's request has the base conversation, and no other fork's turn.
    conversations: dict[str, Any] = {prompt_of(r): r["messages"] for r in api.requests}
    for branch, other in [(budget, luxury), (luxury, budget)]:
        conversation = json.dumps(conversations[branch.prompt])
        assert PROMPT in conversation
        assert other.prompt not in conversation

    await Replayer(
        workflows=[ForkSessionWorkflow], plugins=[ClaudeAgentSDKPlugin()]
    ).replay_workflow(await handle.fetch_history())
