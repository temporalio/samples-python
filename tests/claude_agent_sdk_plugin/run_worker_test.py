"""Drives each scenario's documented entry point.

Each test runs the real ``run_worker.main()`` offline against the test server,
then does what the scenario README does with the Temporal CLI, through the
Python client.
"""

import asyncio
import contextlib
import importlib
import sys
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from typing import Any, TypeVar

import pytest
from temporalio.client import Client, WorkflowContinuedAsNewError, WorkflowHandle
from temporalio.contrib.pydantic import pydantic_data_converter

from claude_agent_sdk_plugin.agent_chat.workflow import ChatWorkflow
from claude_agent_sdk_plugin.human_in_the_loop.workflow import (
    Decision,
    HumanInTheLoopWorkflow,
)
from claude_agent_sdk_plugin.multi_agent.run_worker import (
    BRIEFING,
    RESEARCH_NOTES,
)
from claude_agent_sdk_plugin.multi_agent.workflow import MultiAgentWorkflow
from claude_agent_sdk_plugin.plugin_with_custom_transport.workflow import (
    PluginWithCustomTransportWorkflow,
)
from claude_agent_sdk_plugin.streaming import run_workflow
from claude_agent_sdk_plugin.streaming.workflow import StreamingWorkflow
from claude_agent_sdk_plugin.structured_output.workflow import (
    SupportTicket,
    TriageTicketWorkflow,
)
from claude_agent_sdk_plugin.tools.workflow import ToolsWorkflow

# Reused so the plugin_with_custom_transport entry point runs against a fake `sbx` on PATH.
from tests.claude_agent_sdk_plugin.plugin_with_custom_transport_test import (  # noqa: F401
    fake_sbx,
)

T = TypeVar("T")

TIMEOUT = 120
STREAMING_PROMPT = "Count from one to five, one number per sentence."
HAIKU = (
    "Workers fall and rise\n"
    "history remembers all\n"
    "the work carries on\n"
    "\n"
    "~ haiku-writer"
)


def workflow_id(scenario: str) -> str:
    return f"{scenario}-{uuid.uuid4()}"


def task_queue(scenario: str) -> str:
    return f"claude-agent-sdk-{scenario.replace('_', '-')}"


@contextlib.asynccontextmanager
async def running_main(
    scenario: str, client: Client, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[Callable[[Awaitable[T]], Awaitable[T]]]:
    """Runs the scenario's `run_worker.main()` offline in the background.

    Yields `until`, which awaits an awaitable but fails fast, with the Worker's
    error, if `main()` stops first. On exit, cancels `main()` and waits for its
    Worker to finish shutting down.
    """
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.setenv("TEMPORAL_ADDRESS", client.service_client.config.target_host)
    run_worker = importlib.import_module(
        f"claude_agent_sdk_plugin.{scenario}.run_worker"
    )
    main = asyncio.create_task(run_worker.main())

    async def until(awaitable: Awaitable[T]) -> T:
        step = asyncio.ensure_future(awaitable)
        await asyncio.wait(
            {main, step}, timeout=TIMEOUT, return_when=asyncio.FIRST_COMPLETED
        )
        if main.done():
            step.cancel()
            main.result()
            raise AssertionError("run_worker.main() returned")
        if not step.done():
            step.cancel()
            raise AssertionError("Timed out")
        return step.result()

    try:
        yield until
    finally:
        main.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await main


async def pending_call(
    until: Callable[[Awaitable[Any]], Awaitable[Any]],
    handle: WorkflowHandle,
    query: Any,
    tool_use_id: str,
) -> Any:
    async def poll() -> Any:
        while True:
            for call in await handle.query(query):
                if call.tool_use_id == tool_use_id:
                    return call
            await asyncio.sleep(0.2)

    return await until(poll())


@pytest.mark.parametrize(
    ("scenario", "run", "argument", "expected"),
    [
        (
            "tools",
            ToolsWorkflow.run,
            "Count the r letters in strawberry, then get the weather in Paris.",
            "There are 3 r's in strawberry. It is 21 C and sunny in Paris.",
        ),
        (
            "structured_output",
            TriageTicketWorkflow.run,
            "The app crashes every time I open the settings page.",
            SupportTicket(
                category="bug",
                priority=2,
                summary="The settings page crashes the app when opened.",
            ),
        ),
        (
            "streaming",
            StreamingWorkflow.run,
            STREAMING_PROMPT,
            "One. Two. Three. Four. Five.",
        ),
    ],
)
async def test_execute_workflow(
    scenario: str,
    run: Any,
    argument: str,
    expected: Any,
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if scenario == "structured_output":
        client = await Client.connect(
            client.service_client.config.target_host,
            data_converter=pydantic_data_converter,
        )
    async with running_main(scenario, client, monkeypatch) as until:
        result = await until(
            client.execute_workflow(
                run,
                argument,
                id=workflow_id(scenario),
                task_queue=task_queue(scenario),
            )
        )
    assert result == expected


async def test_multi_agent(client: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    async with running_main("multi_agent", client, monkeypatch) as until:
        briefing = await until(
            client.execute_workflow(
                MultiAgentWorkflow.run,
                "durable execution",
                id=workflow_id("multi-agent"),
                task_queue=task_queue("multi_agent"),
            )
        )
    assert briefing.result == f"Final briefing: {BRIEFING}"
    assert briefing.messages_by_agent["researcher"] == [RESEARCH_NOTES]
    assert briefing.messages_by_agent["writer"] == [BRIEFING]
    assert briefing.messages_by_agent["coordinator"][-1] == briefing.result


async def test_agent_chat(client: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    async with running_main("agent_chat", client, monkeypatch) as until:
        chat_id = workflow_id("agent-chat")
        handle = await client.start_workflow(
            "ChatWorkflow",
            {},
            id=chat_id,
            task_queue=task_queue("agent_chat"),
        )
        replies = [
            await until(
                handle.execute_update(
                    ChatWorkflow.send_message, f"Message {number}, my name is Ada."
                )
            )
            for number in range(1, 4)
        ]
        # The third message fills the run, so the fourth is answered by a new
        # run that resumes Claude Code's session.
        with pytest.raises(WorkflowContinuedAsNewError):
            await until(handle.result(follow_runs=False))
        replies.append(
            await until(
                client.get_workflow_handle(chat_id).execute_update(
                    ChatWorkflow.send_message, "What is my name?"
                )
            )
        )
        await until(
            client.get_workflow_handle(chat_id).signal(ChatWorkflow.end_conversation)
        )
        await until(client.get_workflow_handle(chat_id).result())
    assert replies == [f"Offline reply {n} in this conversation." for n in range(1, 5)]


@pytest.mark.parametrize(
    ("approved", "expected", "creates_file"),
    [
        (True, "Created hello.txt.", True),
        (False, "Understood. I did not create hello.txt.", False),
    ],
)
async def test_human_in_the_loop(
    approved: bool,
    expected: str,
    creates_file: bool,
    client: Client,
    workspace: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with running_main("human_in_the_loop", client, monkeypatch) as until:
        handle = await client.start_workflow(
            HumanInTheLoopWorkflow.run,
            "Create hello.txt with a greeting.",
            id=workflow_id("human-in-the-loop"),
            task_queue=task_queue("human_in_the_loop"),
        )
        request = await pending_call(
            until, handle, HumanInTheLoopWorkflow.pending_tool_calls, "toolu_hello"
        )
        assert request.tool_name == "Bash"
        assert request.tool_input == {
            "command": "echo 'Hello from Claude Code' > hello.txt"
        }
        await until(
            handle.execute_update(
                HumanInTheLoopWorkflow.decide, Decision("toolu_hello", approved)
            )
        )
        result = await until(handle.result())
    assert result == expected
    assert (workspace / "hello.txt").exists() is creates_file


async def test_plugin_with_custom_transport(
    client: Client,
    fake_sbx: Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with running_main(
        "plugin_with_custom_transport", client, monkeypatch
    ) as until:
        result = await until(
            client.execute_workflow(
                PluginWithCustomTransportWorkflow.run,
                "Write a haiku about durable execution.",
                id=workflow_id("plugin-with-custom-transport"),
                task_queue=task_queue("plugin_with_custom_transport"),
            )
        )
    assert result == HAIKU


async def test_streaming_run_workflow_prints_deltas_and_result(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["run_workflow.py"])
    async with running_main("streaming", client, monkeypatch) as until:
        await until(run_workflow.main())
    assert capsys.readouterr().out.endswith(
        "One. Two. Three. Four. Five.\nFinal result: One. Two. Three. Four. Five.\n"
    )
