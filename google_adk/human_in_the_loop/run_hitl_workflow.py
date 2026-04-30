"""Human-in-the-loop example — demonstrates approval workflow.

This starter:
1. Starts the workflow with a prompt that will trigger a sensitive tool
2. Polls for pending approvals
3. Approves the tool call via signal
4. Waits for the final result
"""

import asyncio

from temporalio.client import Client
from temporalio.contrib.google_adk_agents import GoogleAdkPlugin

from google_adk.human_in_the_loop.workflows.hitl_workflow import (
    ApprovalSignal,
    HumanInTheLoopWorkflow,
)

WORKFLOW_ID = "google-adk-hitl-workflow"


async def main():
    client = await Client.connect(
        "localhost:7233",
        plugins=[GoogleAdkPlugin()],
    )

    # Start the workflow (don't await result yet)
    handle = await client.start_workflow(
        HumanInTheLoopWorkflow.run,
        "Send an email to alice@example.com with subject 'Hello' and body 'How are you?'",
        id=WORKFLOW_ID,
        task_queue="google-adk-hitl-task-queue",
    )
    print(f"Workflow started: {handle.id}")

    # Poll for pending approvals
    print("Waiting for tool call to require approval...")
    pending = []
    for _ in range(30):
        pending = await handle.query(HumanInTheLoopWorkflow.get_pending_approvals)
        if pending:
            break
        await asyncio.sleep(1)

    if not pending:
        print("No pending approvals found (agent may not have used a sensitive tool)")
        result = await handle.result()
        print(f"Result: {result}")
        return

    # Show pending approval and approve it
    for call in pending:
        print("\nPending approval:")
        print(f"  Tool: {call.tool_name}")
        print(f"  Arguments: {call.arguments}")
        print(f"  Approving call {call.call_id}...")

        await handle.signal(
            HumanInTheLoopWorkflow.approve,
            ApprovalSignal(call_id=call.call_id, approved=True),
        )

    # Wait for final result
    result = await handle.result()
    print(f"\nFinal result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
