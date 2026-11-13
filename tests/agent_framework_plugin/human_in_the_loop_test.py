import asyncio
import uuid

import pytest
from temporalio.client import Client, WorkflowHandle, WorkflowUpdateFailedError
from temporalio.worker import Worker

from agent_framework_plugin.human_in_the_loop.workflow import (
    ApprovalRequest,
    HumanInTheLoopWorkflow,
)
from tests.agent_framework_plugin._fake_chat_client import (
    function_call_response,
    scripted_plugin,
    text_response,
)
from tests.agent_framework_plugin.helpers import (
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


async def _pending(handle: WorkflowHandle) -> list[ApprovalRequest]:
    for _ in range(100):
        pending = await handle.query(HumanInTheLoopWorkflow.pending_approvals)
        if pending:
            return pending
        await asyncio.sleep(0.1)
    raise AssertionError("the workflow never surfaced an approval request")


async def test_approve(client: Client) -> None:
    plugin, factory = scripted_plugin(_script("Deleted /tmp/report.txt."))
    client = with_plugin(client, plugin)
    task_queue = f"agent-framework-human-in-the-loop-{uuid.uuid4()}"

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[HumanInTheLoopWorkflow],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            HumanInTheLoopWorkflow.run,
            "Please delete /tmp/report.txt",
            id=f"agent-framework-human-in-the-loop-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        (request,) = await _pending(handle)
        assert request.tool_name == "delete_file"
        assert request.arguments == {"path": "/tmp/report.txt"}
        assert request.request_id
        outcome = await handle.execute_update(HumanInTheLoopWorkflow.decide, "approve")
        result = await handle.result()

    assert outcome == "approve"
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
    task_queue = f"agent-framework-hitl-reject-{uuid.uuid4()}"

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[HumanInTheLoopWorkflow],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            HumanInTheLoopWorkflow.run,
            "Please delete /tmp/report.txt",
            id=f"agent-framework-hitl-reject-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        await _pending(handle)
        outcome = await handle.execute_update(HumanInTheLoopWorkflow.decide, "reject")
        result = await handle.result()

    assert outcome == "reject"
    assert result == "Understood, I did not delete it."
    # The tool never ran: the model got Agent Framework's rejection result.
    (tool_result,) = function_results(factory().calls[-1]["messages"])
    assert "deleted" not in tool_result
    assert "reject" in tool_result.lower()
    assert await count_scheduled_activities(handle) == {INVOKE_MODEL: 2}


async def test_validator_rejects_other_decisions(client: Client) -> None:
    plugin, _ = scripted_plugin(_script("Deleted /tmp/report.txt."))
    client = with_plugin(client, plugin)
    task_queue = f"agent-framework-hitl-validator-{uuid.uuid4()}"

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[HumanInTheLoopWorkflow],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            HumanInTheLoopWorkflow.run,
            "Please delete /tmp/report.txt",
            id=f"agent-framework-hitl-validator-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        await _pending(handle)
        # The validator keeps anything but approve or reject out of history.
        with pytest.raises(WorkflowUpdateFailedError):
            await handle.execute_update(HumanInTheLoopWorkflow.decide, "maybe")
        # The Workflow is still waiting and takes the real decision.
        await handle.execute_update(HumanInTheLoopWorkflow.decide, "approve")
        assert await handle.result() == "Deleted /tmp/report.txt."
