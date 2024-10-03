import uuid

import pytest
from temporalio.client import Client, WorkflowHandle, WorkflowUpdateStage
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from message_passing.waiting_for_handlers_and_compensation import (
    WorkflowExitType,
    WorkflowInput,
)
from message_passing.waiting_for_handlers_and_compensation.starter import (
    TASK_QUEUE,
)
from message_passing.waiting_for_handlers_and_compensation.workflows import (
    WaitingForHandlersAndCompensationWorkflow,
)


async def test_waiting_for_handlers_and_compensation(
    client: Client, env: WorkflowEnvironment
):
    if env.supports_time_skipping:
        pytest.skip(
            "Java test server: https://github.com/temporalio/sdk-java/issues/1903"
        )
    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[WaitingForHandlersAndCompensationWorkflow],
    ):
        await starter(
            WorkflowExitType.SUCCESS,
            client,
        )


async def starter(exit_type: WorkflowExitType, cl: Client):
    wf_handle = await cl.start_workflow(
        WaitingForHandlersAndCompensationWorkflow.run,
        WorkflowInput(exit_type=exit_type),
        id=str(uuid.uuid4()),
        task_queue=TASK_QUEUE,
    )
    await _check_run(wf_handle, exit_type)


async def _check_run(
    wf_handle: WorkflowHandle,
    exit_type: WorkflowExitType,
):
    try:
        up_handle = await wf_handle.start_update(
            WaitingForHandlersAndCompensationWorkflow.my_update,
            wait_for_stage=WorkflowUpdateStage.ACCEPTED,
        )
    except Exception as e:
        print(
            f"    🔴 caught exception while starting update: {e}: {e.__cause__ or ''}"
        )

    if exit_type == WorkflowExitType.CANCELLATION:
        await wf_handle.cancel()

    try:
        await up_handle.result()
        print("    🟢 caller received update result")
    except Exception as e:
        print(
            f"    🔴 caught exception while waiting for update result: {e}: {e.__cause__ or ''}"
        )

    if exit_type == WorkflowExitType.CONTINUE_AS_NEW:
        await _check_run(wf_handle, WorkflowExitType.SUCCESS)
    else:
        try:
            await wf_handle.result()
            print("    🟢 caller received workflow result")
        except Exception as e:
            print(
                f"    🔴 caught exception while waiting for workflow result: {e}: {e.__cause__ or ''}"
            )
