"""Execute the Human-in-the-Loop Functional API workflow.

This script demonstrates the approval workflow:
1. Starts the workflow with a payment request
2. Queries for the pending approval
3. Sends a signal with the approval decision
4. Gets the final result
"""

import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from langgraph_plugin.functional_api.human_in_the_loop.workflow import (
    ApprovalRequest,
    ApprovalWorkflow,
)


async def main() -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    # Create approval request
    request = ApprovalRequest(
        request_type="payment",
        amount=500.00,
        request_data={
            "recipient": "vendor@example.com",
            "description": "Invoice #1234",
        },
    )

    # Start the workflow
    handle = await client.start_workflow(
        ApprovalWorkflow.run,
        request,
        id="approval-functional-workflow",
        task_queue="langgraph-functional-approval",
    )

    print(f"Started workflow: {handle.id}")

    # Wait a moment for the workflow to hit the interrupt
    await asyncio.sleep(1)

    # Query the pending approval
    pending = await handle.query(ApprovalWorkflow.get_pending_approval)
    if pending:
        print(f"\nPending approval: {pending.get('message')}")
        print(f"Risk level: {pending.get('risk_level')}")

    # Simulate human approval
    print("\nProviding approval...")
    await handle.signal(
        ApprovalWorkflow.provide_approval,
        {
            "approved": True,
            "approver": "manager@example.com",
            "reason": "Approved for vendor payment",
        },
    )

    # Wait for completion
    result = await handle.result()

    print(f"\nResult: {result.get('result')}")
    print(f"Executed: {result.get('executed')}")


if __name__ == "__main__":
    asyncio.run(main())
