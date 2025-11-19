import asyncio
import uuid
from typing import Optional

from temporalio.client import Client
from temporalio.worker import Worker

from nexus_sync_operations.caller.workflows import CallerWorkflow

NAMESPACE = "nexus-sync-operations-caller-namespace"
TASK_QUEUE = "nexus-sync-operations-caller-task-queue"


async def execute_caller_workflow(
    client: Optional[Client] = None,
) -> None:
    # Use separate task queue for caller
    caller_task_queue = "nexus-sync-operations-caller-task-queue"
    
    client = client or await Client.connect(
        "localhost:7233",
        namespace=NAMESPACE,
    )

    # Start worker in the background, keep it running
    async with Worker(
        client,
        task_queue=caller_task_queue,
        workflows=[CallerWorkflow],
        # Caller doesn't need activities or nexus handlers - 
        # it only calls operations on remote endpoint
    ):
        log = await client.execute_workflow(
            CallerWorkflow.run[None],
            id=str(uuid.uuid4()),
            task_queue=caller_task_queue,  # Use caller's task queue
        )
        for line in log:
            print(line)
        # Worker stays alive until the workflow completes


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(execute_caller_workflow())
    except KeyboardInterrupt:
        loop.run_until_complete(loop.shutdown_asyncgens())
