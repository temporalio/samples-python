"""Tests for the approval_wait_condition LangGraph sample."""

import uuid

from temporalio.client import Client, WorkflowHandle
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.worker import Worker

from langgraph_samples.human_in_the_loop.approval_wait_condition.graph import (
    build_approval_graph,
    notify_approver,
)
from langgraph_samples.human_in_the_loop.approval_wait_condition.workflow import (
    ApprovalRequest,
    ApprovalWorkflow,
)


async def test_approval_wait_condition_approved(client: Client) -> None:
    """Test approval workflow when request is approved."""
    task_queue = f"approval-test-{uuid.uuid4()}"

    plugin = LangGraphPlugin(graphs={"approval_workflow": build_approval_graph})

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[ApprovalWorkflow],
        activities=[notify_approver],
        plugins=[plugin],
    ):
        # Start the workflow
        handle: WorkflowHandle[ApprovalWorkflow, dict] = await client.start_workflow(
            ApprovalWorkflow.run,
            ApprovalRequest(request_type="expense", amount=500.0),
            id=f"approval-{uuid.uuid4()}",
            task_queue=task_queue,
        )

        # Wait for the workflow to reach the approval point
        import asyncio

        for _ in range(20):
            status = await handle.query(ApprovalWorkflow.get_status)
            if status == "waiting_for_approval":
                break
            await asyncio.sleep(0.1)

        assert status == "waiting_for_approval"

        # Query the pending approval
        pending = await handle.query(ApprovalWorkflow.get_pending_approval)
        assert pending is not None
        assert pending["amount"] == 500.0
        assert pending["risk_level"] == "medium"

        # Send approval signal
        await handle.signal(
            ApprovalWorkflow.provide_approval,
            {"approved": True, "reason": "Looks good", "approver": "manager"},
        )

        # Wait for result
        result = await handle.result()

        assert result["approved"] is True
        assert result["executed"] is True
        assert "Successfully processed" in result["result"]
        assert "manager" in result["result"]


async def test_approval_wait_condition_rejected(client: Client) -> None:
    """Test approval workflow when request is rejected."""
    task_queue = f"approval-test-{uuid.uuid4()}"

    plugin = LangGraphPlugin(graphs={"approval_workflow": build_approval_graph})

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[ApprovalWorkflow],
        activities=[notify_approver],
        plugins=[plugin],
    ):
        handle: WorkflowHandle[ApprovalWorkflow, dict] = await client.start_workflow(
            ApprovalWorkflow.run,
            ApprovalRequest(request_type="purchase", amount=5000.0),
            id=f"approval-{uuid.uuid4()}",
            task_queue=task_queue,
        )

        # Wait for approval state
        import asyncio

        for _ in range(20):
            status = await handle.query(ApprovalWorkflow.get_status)
            if status == "waiting_for_approval":
                break
            await asyncio.sleep(0.1)

        # Verify high risk level for large amount
        pending = await handle.query(ApprovalWorkflow.get_pending_approval)
        assert pending is not None
        assert pending["risk_level"] == "high"

        # Reject the request
        await handle.signal(
            ApprovalWorkflow.provide_approval,
            {"approved": False, "reason": "Budget exceeded", "approver": "cfo"},
        )

        result = await handle.result()

        assert result["approved"] is False
        assert result["executed"] is False
        assert "rejected" in result["result"]
        assert "cfo" in result["result"]
