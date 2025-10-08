import asyncio
import uuid

from temporalio.client import Client
from temporalio.worker import Worker

from eager_wf_start.activities import greeting
from eager_wf_start.workflows import EagerWorkflow

TASK_QUEUE = "eager-wf-start-task-queue"

async def main():
    
    # Note that the worker and client run in the same process and share the same client connection.
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[EagerWorkflow],
        activities=[greeting],
    )

    # Run worker in the background
    async with worker:
        # Start workflow(s) while worker is running
        wf_handle = await client.start_workflow(
            EagerWorkflow.run,
            "Temporal",
            id=f"eager-workflow-id-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
            request_eager_start=True,
        )
    
        # This is an internal flag not intended to be used publicly.
        # It is used here purely to display that the workflow was eagerly started.
        print(f"Workflow eagerly started: {wf_handle.__temporal_eagerly_started}")
        print(await wf_handle.result())


if __name__ == "__main__":
    asyncio.run(main())
