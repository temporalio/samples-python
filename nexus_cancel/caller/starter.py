"""
Starter script to execute the caller workflow that demonstrates Nexus cancellation.
"""

import asyncio
import uuid

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from nexus_cancel.caller.workflows import HelloCallerWorkflow

NAMESPACE = "my-caller-namespace"
TASK_QUEUE = "my-caller-workflow-task-queue"


async def main():
    """Execute the caller workflow."""
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    config.setdefault("namespace", NAMESPACE)
    client = await Client.connect(**config)

    workflow_id = f"hello-caller-{uuid.uuid4()}"

    # Start the workflow
    handle = await client.start_workflow(
        HelloCallerWorkflow.run,
        "Nexus",
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )

    print(f"Started workflow workflowId: {handle.id} runId: {handle.result_run_id}")

    # Wait for result
    result = await handle.result()
    print(f"Workflow result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
