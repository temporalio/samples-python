import asyncio
import json
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
)
from temporalio.exceptions import CancelledError
from temporalio.worker import Replayer, Worker

from claude_agent_sdk_plugin.human_in_the_loop.run_worker import (
    OFFLINE_ANSWERS,
    TOOL_USE_ID,
    tool_result,
)
from claude_agent_sdk_plugin.human_in_the_loop.workflow import (
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
) -> ToolRequest:
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


@pytest.mark.parametrize("approved", [True, False])
def test_decided_tool_call_is_not_pending(approved: bool) -> None:
    instance = HumanInTheLoopWorkflow()
    request = ToolRequest(TOOL_USE_ID, "Bash", {"command": "echo hello"})
    instance.pending = request
    assert instance.pending_tool_calls() == request

    # Simulate a query after the update, before the waiting callback resumes.
    HumanInTheLoopWorkflow.decide(instance, approved)

    assert instance.pending_tool_calls() is None
    call = json.dumps([request.tool_name, request.tool_input], sort_keys=True)
    assert instance.decisions[call] is approved
    with pytest.raises(ValueError, match="No tool call is waiting for a decision"):
        instance.validate_decide(approved)


async def test_approved_tool_call_runs(client: Client, workspace: Path) -> None:
    async with started(client) as (handle, _):
        request = await wait_for_request(handle)
        assert request == ToolRequest(
            TOOL_USE_ID,
            "Bash",
            {"command": "echo 'Hello from Claude Code' > hello.txt"},
        )
        assert not (workspace / "hello.txt").exists()

        await handle.execute_update(HumanInTheLoopWorkflow.decide, True)

        assert await handle.result() == "Created hello.txt."
    assert (workspace / "hello.txt").read_text() == "Hello from Claude Code\n"
    await assert_replays(handle)


async def test_denied_tool_call_reaches_the_model(
    client: Client, workspace: Path
) -> None:
    async with started(client) as (handle, api):
        await wait_for_request(handle)

        await handle.execute_update(HumanInTheLoopWorkflow.decide, False)

        assert await handle.result() == "Understood. I did not create hello.txt."
    assert not (workspace / "hello.txt").exists()
    result = tool_result(api.requests[-1])
    assert result["is_error"] is True
    assert "A person denied this tool call" in str(result["content"])
    await assert_replays(handle)


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


async def test_decision_survives_a_worker_restart(
    client: Client, workspace: Path
) -> None:
    task_queue = f"claude-agent-sdk-human-in-the-loop-{uuid.uuid4()}"

    def worker() -> Worker:
        return Worker(
            client,
            task_queue=task_queue,
            workflows=[HumanInTheLoopWorkflow],
            plugins=[ClaudeAgentSDKPlugin()],
        )

    with scripted_api(OFFLINE_ANSWERS) as api:
        async with worker():
            handle = await client.start_workflow(
                HumanInTheLoopWorkflow.run,
                TASK,
                id=f"human-in-the-loop-{uuid.uuid4()}",
                task_queue=task_queue,
            )
            await wait_for_request(handle)

        decision = asyncio.create_task(
            handle.execute_update(HumanInTheLoopWorkflow.decide, True)
        )
        async with worker():
            await decision
            result = asyncio.create_task(handle.result())
            while not result.done():
                pending = await handle.query(HumanInTheLoopWorkflow.pending_tool_calls)
                assert pending is None
                await asyncio.sleep(0.2)
            assert await result == "Created hello.txt."
    assert (workspace / "hello.txt").read_text() == "Hello from Claude Code\n"
    assert api.asked.count("hello.txt") == 2
    await assert_replays(handle)
