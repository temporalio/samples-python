import asyncio
import uuid

import pytest
from temporalio.client import Client, WorkflowHandle, WorkflowUpdateFailedError
from temporalio.worker import Worker

from microsoft_agent_framework_plugin.human_in_the_loop.workflow import (
    ApprovalRequest,
    Decision,
    HumanInTheLoopWorkflow,
)
from tests.microsoft_agent_framework_plugin._fake_chat_client import (
    function_call_response,
    scripted_plugin,
    text_response,
)
from tests.microsoft_agent_framework_plugin.helpers import (
    INVOKE_MODEL,
    count_scheduled_activities,
    function_results,
    with_plugin,
)


def _script(final_text: str) -> list:
    # The model asks to delete the file; after the decision it reports back.
    return [
        function_call_response(
            "delete_file", {"path": "/tmp/report.txt"}, call_id="call-1"
        ),
        text_response(final_text),
    ]


async def _pending(
    handle: WorkflowHandle, *, after: str | None = None
) -> list[ApprovalRequest]:
    """Return the pending requests once there are any, other than ``after``."""
    for _ in range(100):
        pending = await handle.query(HumanInTheLoopWorkflow.pending_approvals)
        if pending and all(request.request_id != after for request in pending):
            return pending
        await asyncio.sleep(0.1)
    raise AssertionError("the workflow never surfaced an approval request")


async def test_approve(client: Client) -> None:
    plugin, factory = scripted_plugin(_script("Deleted /tmp/report.txt."))
    client = with_plugin(client, plugin)
    task_queue = f"microsoft-agent-framework-human-in-the-loop-{uuid.uuid4()}"

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[HumanInTheLoopWorkflow],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            HumanInTheLoopWorkflow.run,
            "Please delete /tmp/report.txt",
            id=f"microsoft-agent-framework-human-in-the-loop-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        (request,) = await _pending(handle)
        assert request.tool_name == "delete_file"
        assert request.arguments == {"path": "/tmp/report.txt"}
        assert request.request_id
        outcome = await handle.execute_update(
            HumanInTheLoopWorkflow.decide,
            Decision(request_id=request.request_id, approved=True),
        )
        result = await handle.result()

    assert outcome == "approved"
    assert result == "Deleted /tmp/report.txt."
    # Two model calls: the request and the report. The approved tool ran in
    # the Workflow, so it left no Activity, and its result reached the model.
    assert await count_scheduled_activities(handle) == {INVOKE_MODEL: 2}
    assert function_results(factory().calls[-1]["messages"]) == [
        "deleted /tmp/report.txt"
    ]


async def test_reject(client: Client) -> None:
    plugin, factory = scripted_plugin(_script("Understood, I did not delete it."))
    client = with_plugin(client, plugin)
    task_queue = f"microsoft-agent-framework-hitl-reject-{uuid.uuid4()}"

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[HumanInTheLoopWorkflow],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            HumanInTheLoopWorkflow.run,
            "Please delete /tmp/report.txt",
            id=f"microsoft-agent-framework-hitl-reject-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        (request,) = await _pending(handle)
        outcome = await handle.execute_update(
            HumanInTheLoopWorkflow.decide,
            Decision(request_id=request.request_id, approved=False),
        )
        result = await handle.result()

    assert outcome == "rejected"
    assert result == "Understood, I did not delete it."
    # The tool never ran: the model got Agent Framework's rejection result.
    (tool_result,) = function_results(factory().calls[-1]["messages"])
    assert "deleted" not in tool_result
    assert "reject" in tool_result.lower()
    assert await count_scheduled_activities(handle) == {INVOKE_MODEL: 2}


async def test_bad_decisions_are_rejected(client: Client) -> None:
    # Two approval rounds, so a decision for the first request is stale while
    # the second one is pending.
    plugin, _ = scripted_plugin(
        [
            function_call_response(
                "delete_file", {"path": "/tmp/a.txt"}, call_id="call-1"
            ),
            function_call_response(
                "delete_file", {"path": "/tmp/b.txt"}, call_id="call-2"
            ),
            text_response("Deleted both files."),
        ]
    )
    client = with_plugin(client, plugin)
    task_queue = f"microsoft-agent-framework-hitl-bad-{uuid.uuid4()}"

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[HumanInTheLoopWorkflow],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            HumanInTheLoopWorkflow.run,
            "Please delete /tmp/a.txt and /tmp/b.txt",
            id=f"microsoft-agent-framework-hitl-bad-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        (first,) = await _pending(handle)
        assert first.arguments == {"path": "/tmp/a.txt"}
        await handle.execute_update(
            HumanInTheLoopWorkflow.decide,
            Decision(request_id=first.request_id, approved=True),
        )
        (second,) = await _pending(handle, after=first.request_id)
        assert second.arguments == {"path": "/tmp/b.txt"}

        # The validator keeps an empty id out of history; the handler fails the
        # Update for a stale id and for an unknown one. The Workflow keeps waiting.
        for bad in ("", first.request_id, "not-a-request"):
            with pytest.raises(WorkflowUpdateFailedError):
                await handle.execute_update(
                    HumanInTheLoopWorkflow.decide,
                    Decision(request_id=bad, approved=True),
                )
        assert await handle.query(HumanInTheLoopWorkflow.pending_approvals) == [second]

        await handle.execute_update(
            HumanInTheLoopWorkflow.decide,
            Decision(request_id=second.request_id, approved=True),
        )
        assert await handle.result() == "Deleted both files."
    assert await count_scheduled_activities(handle) == {INVOKE_MODEL: 3}
