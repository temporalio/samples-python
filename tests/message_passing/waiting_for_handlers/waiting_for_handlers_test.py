from enum import Enum

import pytest
from temporalio import client, worker
from temporalio.testing import WorkflowEnvironment

from message_passing.waiting_for_handlers import WorkflowExitType, WorkflowInput
from message_passing.waiting_for_handlers.activities import (
    activity_executed_by_update_handler,
)
from message_passing.waiting_for_handlers.starter import TASK_QUEUE
from message_passing.waiting_for_handlers.workflows import WaitingForHandlersWorkflow


class UpdateExpect(Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class WorkflowExpect(Enum):
    SUCCESS = "success"
    FAILURE = "failure"


@pytest.mark.parametrize(
    ["exit_type_name", "update_expect", "workflow_expect"],
    [
        (WorkflowExitType.SUCCESS.name, UpdateExpect.SUCCESS, WorkflowExpect.SUCCESS),
        (WorkflowExitType.FAILURE.name, UpdateExpect.SUCCESS, WorkflowExpect.FAILURE),
        (
            WorkflowExitType.CANCELLATION.name,
            UpdateExpect.SUCCESS,
            WorkflowExpect.FAILURE,
        ),
    ],
)
async def test_waiting_for_handlers(
    env: WorkflowEnvironment,
    exit_type_name: str,
    update_expect: UpdateExpect,
    workflow_expect: WorkflowExpect,
):
    [exit_type] = [t for t in WorkflowExitType if t.name == exit_type_name]
    if env.supports_time_skipping:
        pytest.skip(
            "Java test server: https://github.com/temporalio/sdk-java/issues/1903"
        )
    async with worker.Worker(
        env.client,
        task_queue=TASK_QUEUE,
        workflows=[WaitingForHandlersWorkflow],
        activities=[
            activity_executed_by_update_handler,
        ],
    ):
        wf_handle = await env.client.start_workflow(
            WaitingForHandlersWorkflow.run,
            WorkflowInput(exit_type=exit_type),
            id="waiting-for-handlers-test",
            task_queue=TASK_QUEUE,
        )
        up_handle = await wf_handle.start_update(
            WaitingForHandlersWorkflow.my_update,
            wait_for_stage=client.WorkflowUpdateStage.ACCEPTED,
        )

        if exit_type == WorkflowExitType.CANCELLATION:
            await wf_handle.cancel()

        if update_expect == UpdateExpect.SUCCESS:
            await up_handle.result()
        else:
            with pytest.raises(client.WorkflowUpdateFailedError):
                await up_handle.result()

        if workflow_expect == WorkflowExpect.SUCCESS:
            await wf_handle.result()
        else:
            with pytest.raises(client.WorkflowFailureError):
                await wf_handle.result()
