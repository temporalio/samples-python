import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from temporalio.client import Client, WorkflowExecutionStatus, WorkflowFailureError
from temporalio.exceptions import CancelledError
from temporalio.worker import Worker

from hello.hello_cancellation import (
    CancellationWorkflow,
    cleanup_activity,
    never_complete_activity,
)


async def test_cancel_workflow(client: Client):
    task_queue_name = str(uuid.uuid4())

    async with Worker(
        client,
        task_queue=task_queue_name,
        workflows=[CancellationWorkflow],
        activities=[cleanup_activity, never_complete_activity],
        activity_executor=ThreadPoolExecutor(5),
    ):
        handle = await client.start_workflow(
            CancellationWorkflow.run,
            id=(str(uuid.uuid4())),
            task_queue=task_queue_name,
        )

        await asyncio.wait_for(
            wait_for_activity_to_start("never_complete_activity", handle),
            timeout=5,
        )

        await handle.cancel()

        with pytest.raises(WorkflowFailureError) as err:
            await handle.result()
        assert isinstance(err.value.cause, CancelledError)

        assert WorkflowExecutionStatus.CANCELED == (await handle.describe()).status


async def wait_for_activity_to_start(activity_name, handle):
    while not (await has_activity_started(activity_name, handle)):
        await asyncio.sleep(0.2)


async def has_activity_started(activity_name, handle):
    pending_activities = (await handle.describe()).raw_description.pending_activities
    for pending_activity in pending_activities:
        if pending_activity.activity_type.name == activity_name:
            return True

    return False
