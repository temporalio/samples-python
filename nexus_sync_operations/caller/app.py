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
    client = client or await Client.connect(
        "localhost:7233",
        namespace=NAMESPACE,
    )

    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[CallerWorkflow],
    ):
        await client.execute_workflow(
            CallerWorkflow.run,
            id=str(uuid.uuid4()),
            task_queue=TASK_QUEUE,
        )


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(execute_caller_workflow())
    except KeyboardInterrupt:
        loop.run_until_complete(loop.shutdown_asyncgens())
