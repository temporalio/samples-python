import asyncio
import uuid

from temporalio.client import Client, WorkflowExecutionStatus
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from microsoft_agent_framework_plugin.continue_as_new.workflow import (
    ChatInput,
    ChatWorkflow,
)
from tests.microsoft_agent_framework_plugin._fake_chat_client import scripted_plugin
from tests.microsoft_agent_framework_plugin.helpers import (
    count_scheduled_activities,
    with_plugin,
)


async def test_continue_as_new_carries_the_session() -> None:
    """Drive a chat across a continue-as-new boundary.

    One turn is enough history for the server to suggest continue-as-new at
    the lowered threshold. The first run hands its session to a fresh run,
    which takes a second turn on the carried transcript and ends normally.
    """
    plugin, factory = scripted_plugin(["First reply.", "Second reply."])

    # The server suggests continue-as-new once history passes a threshold
    # (4096 events by default). Lower it so one turn trips the suggestion.
    async with await WorkflowEnvironment.start_local(
        dev_server_extra_args=[
            "--dynamic-config-value",
            "limit.historyCount.suggestContinueAsNew=5",
        ]
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
