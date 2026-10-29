import asyncio
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from temporalio.api.enums.v1 import EventType
from temporalio.claude_agent_sdk import ClaudeAgentSDKPlugin
from temporalio.client import (
    Client,
    WorkflowFailureError,
    WorkflowHandle,
    WorkflowUpdateFailedError,
)
from temporalio.exceptions import CancelledError
from temporalio.worker import Replayer, Worker

from claude_agent_sdk_plugin.human_in_the_loop.run_worker import (
    OFFLINE_ANSWERS,
    TOOL_USE_ID,
    tool_result,
)
from claude_agent_sdk_plugin.human_in_the_loop.workflow import (
    Decision,
    HumanInTheLoopWorkflow,
    ToolRequest,
)
from claude_agent_sdk_plugin.offline import ScriptedApi, scripted_api

TASK = "Create hello.txt with a greeting."


@asynccontextmanager
async def started(
    client: Client,
) -> AsyncIterator[tuple[WorkflowHandle[HumanInTheLoopWorkflow, str], ScriptedApi]]:
    task_queue = f"claude-agent-sdk-human-in-the-loop-{uuid.uuid4()}"
    with scripted_api(OFFLINE_ANSWERS) as api:
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[HumanInTheLoopWorkflow],
            plugins=[ClaudeAgentSDKPlugin()],
        ):
            handle = await client.start_workflow(
                HumanInTheLoopWorkflow.run,
                TASK,
                id=f"human-in-the-loop-{uuid.uuid4()}",
                task_queue=task_queue,
            )
            yield handle, api


async def wait_for_request(
    handle: WorkflowHandle[HumanInTheLoopWorkflow, str],
) -> list[ToolRequest]:
    for _ in range(300):
        pending = await handle.query(HumanInTheLoopWorkflow.pending_tool_calls)
        if pending:
            return pending
        await asyncio.sleep(0.2)
    raise AssertionError("No tool call is waiting for a decision")


async def assert_replays(handle: WorkflowHandle[HumanInTheLoopWorkflow, str]) -> None:
    await Replayer(
        workflows=[HumanInTheLoopWorkflow], plugins=[ClaudeAgentSDKPlugin()]
    ).replay_workflow(await handle.fetch_history())


async def test_approved_tool_call_runs(client: Client, workspace: Path) -> None:
    async with started(client) as (handle, _):
        [request] = await wait_for_request(handle)
        assert request == ToolRequest(
            TOOL_USE_ID,
            "Bash",
            {"command": "echo 'Hello from Claude Code' > hello.txt"},
        )
        assert not (workspace / "hello.txt").exists()

        await handle.execute_update(
            HumanInTheLoopWorkflow.decide, Decision(TOOL_USE_ID, approved=True)
        )

        assert await handle.result() == "Created hello.txt."
    assert (workspace / "hello.txt").read_text() == "Hello from Claude Code\n"
    await assert_replays(handle)


async def test_denied_tool_call_reaches_the_model(
    client: Client, workspace: Path
) -> None:
    async with started(client) as (handle, api):
        await wait_for_request(handle)

        await handle.execute_update(
            HumanInTheLoopWorkflow.decide, Decision(TOOL_USE_ID, approved=False)
        )

        assert await handle.result() == "Understood. I did not create hello.txt."
    assert not (workspace / "hello.txt").exists()
    result = tool_result(api.requests[-1])
    assert result["is_error"] is True
    assert "A person denied this tool call" in str(result["content"])
    await assert_replays(handle)


async def test_decision_for_unknown_tool_call_is_rejected(client: Client) -> None:
    async with started(client) as (handle, _):
        await wait_for_request(handle)

        with pytest.raises(WorkflowUpdateFailedError) as rejected:
            await handle.execute_update(
                HumanInTheLoopWorkflow.decide, Decision("toolu_other", approved=True)
            )
        assert "No pending tool call toolu_other" in str(rejected.value.cause)

        await handle.execute_update(
            HumanInTheLoopWorkflow.decide, Decision(TOOL_USE_ID, approved=False)
        )
        await handle.result()


async def test_cancel_while_waiting_ends_the_workflow(
    client: Client, workspace: Path
) -> None:
    async with started(client) as (handle, _):
        await wait_for_request(handle)

        await handle.cancel()

        with pytest.raises(WorkflowFailureError) as failure:
            await handle.result()
        assert isinstance(failure.value.cause, CancelledError)

    history = await handle.fetch_history()
    assert (
        history.events[-1].event_type
        == EventType.EVENT_TYPE_WORKFLOW_EXECUTION_CANCELED
    )
    assert not (workspace / "hello.txt").exists()
    await assert_replays(handle)
