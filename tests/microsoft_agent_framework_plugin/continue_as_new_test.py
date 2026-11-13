import asyncio
import uuid
from collections.abc import Awaitable, Mapping, Sequence
from typing import Any

from agent_framework import ChatResponse, ChatResponseUpdate, Message, ResponseStream
from temporalio.api.enums.v1 import EventType
from temporalio.client import Client, WorkflowExecutionStatus, WorkflowHandle
from temporalio.microsoft_agent_framework import MicrosoftAgentFrameworkPlugin
from temporalio.microsoft_agent_framework.testing import FakeChatClient, ScriptEntry
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from microsoft_agent_framework_plugin.continue_as_new.workflow import (
    ChatInput,
    ChatWorkflow,
)
from tests.microsoft_agent_framework_plugin._fake_chat_client import (
    MODEL,
    scripted_plugin,
)
from tests.microsoft_agent_framework_plugin.helpers import (
    count_scheduled_activities,
    with_plugin,
)

# The server suggests continue-as-new once history passes a threshold (4096
# events by default). Lower it so one turn trips the suggestion.
SUGGEST_EARLY = [
    "--dynamic-config-value",
    "limit.historyCount.suggestContinueAsNew=5",
]


async def test_continue_as_new_carries_the_session() -> None:
    """Drive a chat across a continue-as-new boundary.

    One turn is enough history for the server to suggest continue-as-new at
    the lowered threshold. The first run hands its session to a fresh run,
    which takes a second turn on the carried transcript and ends normally.
    """
    plugin, factory = scripted_plugin(["First reply.", "Second reply."])

    async with await WorkflowEnvironment.start_local(
        dev_server_extra_args=SUGGEST_EARLY
    ) as env:
        client = with_plugin(env.client, plugin)
        task_queue = f"microsoft-agent-framework-chat-{uuid.uuid4()}"
        workflow_id = f"microsoft-agent-framework-chat-{uuid.uuid4()}"

        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[ChatWorkflow],
            max_cached_workflows=0,
        ):
            handle = await client.start_workflow(
                ChatWorkflow.run,
                ChatInput(),
                id=workflow_id,
                task_queue=task_queue,
            )
            first_run_id = handle.result_run_id

            assert await handle.execute_update(ChatWorkflow.turn, "Hello") == (
                "First reply."
            )

            # Pin the first run: an unpinned handle follows the chain to the
            # fresh run, which is still running.
            first_run = client.get_workflow_handle(workflow_id, run_id=first_run_id)
            for _ in range(100):
                status = (await first_run.describe()).status
                if status == WorkflowExecutionStatus.CONTINUED_AS_NEW:
                    break
                await asyncio.sleep(0.1)
            else:
                raise AssertionError("the workflow did not continue as new")

            latest = client.get_workflow_handle(workflow_id)
            assert await latest.execute_update(ChatWorkflow.turn, "How are you?") == (
                "Second reply."
            )
            # Two messages carried across the handoff plus two from the new turn.
            transcript = await latest.query(ChatWorkflow.transcript)
            assert [m["text"] for m in transcript] == [
                "Hello",
                "First reply.",
                "How are you?",
                "Second reply.",
            ]
            await latest.signal(ChatWorkflow.end_chat)
            await latest.result()

            # The first run made exactly one model call before it handed off.
            assert (await count_scheduled_activities(first_run)).total() == 1

    # The fresh run rebuilt the session from the carried dict: its first model
    # call already held the first turn.
    _, second_call = factory().calls
    assert [m.text for m in second_call["messages"]] == [
        "Hello",
        "First reply.",
        "How are you?",
    ]


class _SlowFakeChatClient(FakeChatClient):
    """A scripted client that takes ``delay`` seconds per call, so a turn is in progress for a while."""

    def __init__(self, responses: Sequence[ScriptEntry], *, delay: float) -> None:
        super().__init__(responses)
        self.delay = delay

    def _inner_get_response(
        self,
        *,
        messages: Sequence[Message],
        stream: bool,
        options: Mapping[str, Any],
        **kwargs: Any,
    ) -> Awaitable[ChatResponse] | ResponseStream[ChatResponseUpdate, ChatResponse]:
        inner = super()._inner_get_response(
            messages=messages, stream=stream, options=options, **kwargs
        )
        if isinstance(inner, ResponseStream):
            return inner

        async def slow() -> ChatResponse:
            await asyncio.sleep(self.delay)
            return await inner

        return slow()


async def _wait_for_model_calls_started(handle: WorkflowHandle, count: int) -> None:
    """Return once the run's history shows ``count`` model Activities started."""
    for _ in range(200):
        started = 0
        async for event in handle.fetch_history_events():
            if event.event_type == EventType.EVENT_TYPE_ACTIVITY_TASK_STARTED:
                started += 1
        if started >= count:
            return
        await asyncio.sleep(0.05)
    raise AssertionError(f"model call {count} never started")


async def _run_chain(client: Client, workflow_id: str, first_run_id: str) -> list[str]:
    """Return the run ids of a continue-as-new chain, first run first."""
    run_ids = [first_run_id]
    while True:
        handle = client.get_workflow_handle(workflow_id, run_id=run_ids[-1])
        next_run_id = None
        async for event in handle.fetch_history_events():
            if (
                event.event_type
                == EventType.EVENT_TYPE_WORKFLOW_EXECUTION_CONTINUED_AS_NEW
            ):
                attrs = event.workflow_execution_continued_as_new_event_attributes
                next_run_id = attrs.new_execution_run_id
        if not next_run_id:
            return run_ids
        run_ids.append(next_run_id)


async def test_messages_sent_during_a_turn_are_not_lost() -> None:
    """A turn and an end_chat that arrive while a turn is running are honored.

    Each turn is an Update: it completes in the run that accepted it, and
    `all_handlers_finished` lets an accepted turn finish before the handoff, so
    a turn sent during another turn gets its reply from whichever run the
    server delivers it to. The end_chat arrives during the last turn and ends
    the chat after it. Every turn ran exactly once across the chain.
    """
    slow = _SlowFakeChatClient(
        ["First reply.", "Second reply.", "Third reply."], delay=1.5
    )
    plugin = MicrosoftAgentFrameworkPlugin(chat_clients={MODEL: lambda: slow})

    async with await WorkflowEnvironment.start_local(
        dev_server_extra_args=SUGGEST_EARLY
    ) as env:
        client = with_plugin(env.client, plugin)
        task_queue = f"agent-framework-chat-{uuid.uuid4()}"
        workflow_id = f"agent-framework-chat-{uuid.uuid4()}"

        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[ChatWorkflow],
            max_cached_workflows=0,
        ):
            handle = await client.start_workflow(
                ChatWorkflow.run,
                ChatInput(),
                id=workflow_id,
                task_queue=task_queue,
            )
            first_run_id = handle.result_run_id
            assert first_run_id is not None
            first_run = client.get_workflow_handle(workflow_id, run_id=first_run_id)

            first = asyncio.create_task(
                handle.execute_update(ChatWorkflow.turn, "Hello")
            )
            await _wait_for_model_calls_started(first_run, 1)
            # Sent while the first turn's model call is running.
            second = asyncio.create_task(
                handle.execute_update(ChatWorkflow.turn, "And again?")
            )
            assert await first == "First reply."
            assert await second == "Second reply."

            # One turn is enough history to hand off; the chain has moved on.
            for _ in range(100):
                status = (await first_run.describe()).status
                if status == WorkflowExecutionStatus.CONTINUED_AS_NEW:
                    break
                await asyncio.sleep(0.1)
            else:
                raise AssertionError("the workflow did not continue as new")

            latest = client.get_workflow_handle(workflow_id)
            third = asyncio.create_task(
                latest.execute_update(ChatWorkflow.turn, "Last one")
            )
            latest_run = client.get_workflow_handle(
                workflow_id, run_id=(await latest.describe()).run_id
            )
            await _wait_for_model_calls_started(latest_run, 1)
            # Sent while the third turn's model call is running.
            await latest.signal(ChatWorkflow.end_chat)
            assert await third == "Third reply."
            # The chat ends after the turn that was running.
            await latest.result()

            transcript = await latest.query(ChatWorkflow.transcript)
            assert [m["text"] for m in transcript] == [
                "Hello",
                "First reply.",
                "And again?",
                "Second reply.",
                "Last one",
                "Third reply.",
            ]
            # Three model calls across the whole chain: nothing ran twice or not at all.
            run_ids = await _run_chain(client, workflow_id, first_run_id)
            assert len(run_ids) >= 2
            calls = 0
            for run_id in run_ids:
                run = client.get_workflow_handle(workflow_id, run_id=run_id)
                calls += (await count_scheduled_activities(run)).total()
            assert calls == 3
