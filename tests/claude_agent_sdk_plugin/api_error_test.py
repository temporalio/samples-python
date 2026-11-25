import uuid
from typing import Any

import pytest
from temporalio.claude_agent_sdk import ClaudeAgentSDKPlugin
from temporalio.client import Client, WorkflowFailureError, WorkflowUpdateFailedError
from temporalio.exceptions import ApplicationError
from temporalio.worker import Worker

from claude_agent_sdk_plugin.agent_chat.workflow import ChatInput, ChatWorkflow
from claude_agent_sdk_plugin.fork_session.workflow import ForkSessionWorkflow
from claude_agent_sdk_plugin.hooks.workflow import HooksWorkflow
from claude_agent_sdk_plugin.human_in_the_loop.workflow import HumanInTheLoopWorkflow
from claude_agent_sdk_plugin.multi_agent.workflow import MultiAgentWorkflow
from claude_agent_sdk_plugin.offline import ApiError, scripted_api
from claude_agent_sdk_plugin.open_telemetry.workflow import OpenTelemetryWorkflow
from claude_agent_sdk_plugin.plugin_with_custom_transport.workflow import (
    PluginWithCustomTransportWorkflow,
)
from claude_agent_sdk_plugin.streaming.workflow import StreamingWorkflow
from claude_agent_sdk_plugin.structured_output.workflow import TriageTicketWorkflow
from claude_agent_sdk_plugin.tools.workflow import ToolsWorkflow

# Every request gets this answer: the empty key matches any prompt.
REJECTED_KEY = {
    "": ApiError(401, "authentication_error", "invalid x-api-key"),
}

WORKFLOWS: list[tuple[Any, list[Any]]] = [
    (ForkSessionWorkflow, ["Plan a weekend in Lisbon", ["Redo it on a budget."]]),
    (HooksWorkflow, ["Run echo hello."]),
    (HumanInTheLoopWorkflow, ["Create hello.txt with a greeting."]),
    (MultiAgentWorkflow, ["durable execution"]),
    (OpenTelemetryWorkflow, ["How many Python files are here?"]),
    (PluginWithCustomTransportWorkflow, ["Write a haiku."]),
    (StreamingWorkflow, ["Count to five"]),
    (ToolsWorkflow, ["Get the weather in Paris."]),
    (TriageTicketWorkflow, ["The app crashes."]),
]


def assert_claude_code_failed(cause: BaseException | None) -> None:
    assert isinstance(cause, ApplicationError)
    prefix = "Claude Code failed: "
    assert cause.message.startswith(prefix)
    assert cause.message[len(prefix) :].strip(), "the failure gives no reason"


@pytest.mark.parametrize(
    ("workflow_class", "args"), WORKFLOWS, ids=[w.__name__ for w, _ in WORKFLOWS]
)
async def test_api_error_fails_the_workflow(
    client: Client, workflow_class: Any, args: list[Any]
) -> None:
    task_queue = f"claude-agent-sdk-api-error-{uuid.uuid4()}"
    with scripted_api(REJECTED_KEY) as api:
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[workflow_class],
            plugins=[ClaudeAgentSDKPlugin()],
        ):
            handle = await client.start_workflow(
                workflow_class.run,
                args=args,
                id=f"claude-agent-sdk-api-error-{uuid.uuid4()}",
                task_queue=task_queue,
            )
            with pytest.raises(WorkflowFailureError) as failure:
                await handle.result()

    assert api.requests, "Claude Code never called the scripted API"
    assert_claude_code_failed(failure.value.cause)


async def test_api_error_fails_the_chat_message(client: Client) -> None:
    task_queue = f"claude-agent-sdk-api-error-{uuid.uuid4()}"
    with scripted_api(REJECTED_KEY) as api:
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[ChatWorkflow],
            plugins=[ClaudeAgentSDKPlugin()],
        ):
            handle = await client.start_workflow(
                ChatWorkflow.run,
                ChatInput(),
                id=f"claude-agent-sdk-api-error-{uuid.uuid4()}",
                task_queue=task_queue,
            )
            with pytest.raises(WorkflowUpdateFailedError) as failure:
                await handle.execute_update(ChatWorkflow.send_message, "I'm Ada.")
            await handle.signal(ChatWorkflow.end_conversation)
            await handle.result()

    assert api.requests, "Claude Code never called the scripted API"
    assert_claude_code_failed(failure.value.cause)
