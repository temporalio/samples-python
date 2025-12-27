"""Execute the Approval Workflow.

Demonstrates the human-in-the-loop approval pattern:
1. Start a workflow that pauses for approval
2. Query the pending approval details
3. Send an approval signal
4. Get the final result

Usage:
    # First, start the worker in another terminal:
    python -m langgraph_samples.human_in_loop.approval_workflow.run_worker

    # Then run this script:
    python -m langgraph_samples.human_in_loop.approval_workflow.run_workflow
"""

import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from langgraph_samples.human_in_loop.approval_workflow.workflow import (
    ApprovalRequest,
    ApprovalWorkflow,
)

TASK_QUEUE = "langgraph-approval"


async def main() -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    # Example 1: Approve a request
    print("\n" + "=" * 60)
    print("Example 1: Approving a purchase request")
    print("=" * 60)

    handle = await client.start_workflow(
        ApprovalWorkflow.run,
        ApprovalRequest(
            request_type="purchase",
            amount=500.00,
            request_data={"item": "Office supplies", "vendor": "Acme Corp"},
        ),
        id="approval-workflow-approve",
        task_queue=TASK_QUEUE,
    )

    # Wait for the workflow to reach the interrupt
    await asyncio.sleep(1)

    # Query the pending approval
    pending = await handle.query(ApprovalWorkflow.get_pending_approval)
    print(f"\nPending approval: {pending}")

    status = await handle.query(ApprovalWorkflow.get_status)
    print(f"Workflow status: {status}")

    # Send approval signal
    print("\nSending approval signal...")
    await handle.signal(
        ApprovalWorkflow.provide_approval,
        {
            "approved": True,
            "reason": "Within budget",
            "approver": "manager@example.com",
        },
    )

    # Wait for result
    result = await handle.result()
    print(f"\nResult: {result.get('result')}")
    print(f"Executed: {result.get('executed')}")

    # Example 2: Reject a request
    print("\n" + "=" * 60)
    print("Example 2: Rejecting a high-risk request")
    print("=" * 60)

    handle2 = await client.start_workflow(
        ApprovalWorkflow.run,
        ApprovalRequest(
            request_type="transfer",
            amount=50000.00,
            request_data={"destination": "External account"},
        ),
        id="approval-workflow-reject",
        task_queue=TASK_QUEUE,
    )

    await asyncio.sleep(1)

    # Query pending approval
    pending2 = await handle2.query(ApprovalWorkflow.get_pending_approval)
    print(f"\nPending approval: {pending2}")

    # Reject it
    print("\nSending rejection signal...")
    await handle2.signal(
        ApprovalWorkflow.provide_approval,
        {
            "approved": False,
            "reason": "Amount exceeds single-approval limit",
            "approver": "compliance@example.com",
        },
    )

    result2 = await handle2.result()
    print(f"\nResult: {result2.get('result')}")
    print(f"Executed: {result2.get('executed')}")


if __name__ == "__main__":
    asyncio.run(main())
