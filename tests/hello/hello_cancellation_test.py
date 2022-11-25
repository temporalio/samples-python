import asyncio
import uuid

from temporalio.client import Client, WorkflowExecutionStatus, WorkflowFailureError
from temporalio.worker import Worker

from hello.hello_cancellation import (
    CancellationWorkflow,
    cleanup_activity,
    never_complete_activity,
)


async def test_execute_workflow(client: Client):
    task_queue_name = str(uuid.uuid4())

    async with Worker(
        client,
        task_queue=task_queue_name,
        workflows=[CancellationWorkflow],
        activities=[cleanup_activity, never_complete_activity],
    ):
        handle = await client.start_workflow(
            CancellationWorkflow.run,
            id=(str(uuid.uuid4())),
            task_queue=task_queue_name,
        )

        # wait for the activity "never_complete_activity" to heartbeat
        await asyncio.sleep(2)
        await handle.cancel()

        try:
            await handle.result()
            raise RuntimeError("Should not succeed")
        except WorkflowFailureError:
            pass

        assert WorkflowExecutionStatus.CANCELED == (await handle.describe()).status
