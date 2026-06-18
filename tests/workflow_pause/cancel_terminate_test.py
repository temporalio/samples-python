import asyncio
import uuid

import pytest
from temporalio.client import Client, WorkflowFailureError
from temporalio.exceptions import CancelledError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from workflow_pause.cancel_terminate import TASK_QUEUE
from workflow_pause.cancel_terminate.workflow import CancelTerminatePauseWorkflow


async def test_cancellation_runs_cleanup(client: Client, env: WorkflowEnvironment):
    async with Worker(
        client, task_queue=TASK_QUEUE, workflows=[CancelTerminatePauseWorkflow]
    ):
        handle = await client.start_workflow(
            CancelTerminatePauseWorkflow.run,
            20,
            id=f"cancel-terminate-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )
        # Let the workflow start its loop, then cancel it.
        await asyncio.sleep(1)
        await handle.cancel()
        with pytest.raises(WorkflowFailureError) as exc_info:
            await handle.result()
        assert isinstance(exc_info.value.cause, CancelledError)
