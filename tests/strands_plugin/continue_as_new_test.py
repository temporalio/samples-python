import asyncio
import uuid

import pytest
from temporalio.client import Client, WorkflowExecutionStatus
from temporalio.contrib.strands import StrandsPlugin
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from strands_plugin.continue_as_new.workflow import ChatInput, ChatWorkflow
from tests.strands_plugin._mock_model import patch_bedrock


async def test_continue_as_new_carries_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise the full chat lifecycle across a continue-as-new boundary.

    Drives enough history that the server suggests continue-as-new, confirms the
    original run hands its message history off to a fresh run, then takes another
    turn on that resumed run and ends the chat normally.
    """
    patch_bedrock(monkeypatch, ["First reply.", "Second reply."])

    # The server only suggests continue-as-new once history grows past a
    # threshold (~4096 events by default). Lower it so a single turn's worth of
    # history is enough to trip ``is_continue_as_new_suggested()``.
    async with await WorkflowEnvironment.start_local(
        dev_server_extra_args=[
            "--dynamic-config-value",
            "limit.historyCount.suggestContinueAsNew=5",
        ]
    ) as env:
        config = env.client.config()
        config["plugins"] = [*config["plugins"], StrandsPlugin()]
        client = Client(**config)

        task_queue = f"strands-chat-{uuid.uuid4()}"
        workflow_id = f"strands-chat-{uuid.uuid4()}"

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

            original_run_id = handle.result_run_id

            # One turn produces enough events to cross the threshold above.
            reply1 = await handle.execute_update(ChatWorkflow.turn, "Hello")
            assert reply1 == "First reply."

            # The original run should end by continuing-as-new once the in-flight
            # turn drains. Pin to its run id; an unpinned handle would follow the
            # chain to the fresh (still-running) run instead.
            original = client.get_workflow_handle(workflow_id, run_id=original_run_id)
            for _ in range(100):
                desc = await original.describe()
                if desc.status == WorkflowExecutionStatus.CONTINUED_AS_NEW:
                    break
                await asyncio.sleep(0.1)
            else:
                raise AssertionError("workflow did not continue-as-new")

            # The fresh run resumes with the prior turn's history and accepts a
            # new turn, appending to the carried-over messages.
            latest = client.get_workflow_handle(workflow_id)
            reply2 = await latest.execute_update(ChatWorkflow.turn, "How are you?")
            assert reply2 == "Second reply."

            # 2 messages carried across the handoff + 2 from the resumed turn.
            messages = await latest.query(ChatWorkflow.messages)
            assert len(messages) == 4

            await latest.signal(ChatWorkflow.end_chat)
            await latest.result()
