"""Execute the Approval Workflow.

Starts an approval workflow that pauses for human approval.
The worker will print instructions for how to approve/reject.
"""

import asyncio
import uuid

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

    # Generate a unique workflow ID
    workflow_id = f"approval-{uuid.uuid4().hex[:8]}"

    print(f"Starting approval workflow: {workflow_id}")

    handle = await client.start_workflow(
        ApprovalWorkflow.run,
        ApprovalRequest(
            request_type="purchase",
            amount=500.00,
            request_data={"item": "Office supplies", "vendor": "Acme Corp"},
        ),
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )

    print(f"Workflow started. Waiting for result...")
    print(f"\nTo approve/reject, use the run_respond script (see worker output for commands)")

    # Wait for the workflow to complete
    result = await handle.result()

    print(f"\n{'='*60}")
    print(f"Result: {result.get('result')}")
    print(f"Executed: {result.get('executed')}")


if __name__ == "__main__":
    asyncio.run(main())
