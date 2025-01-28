import asyncio

from temporalio import client, common

from message_passing.waiting_for_handlers import (
    TASK_QUEUE,
    WORKFLOW_ID,
    WorkflowExitType,
    WorkflowInput,
)
from message_passing.waiting_for_handlers.workflows import WaitingForHandlersWorkflow


async def starter(exit_type: WorkflowExitType):
    cl = await client.Client.connect("localhost:7233")
    wf_handle = await cl.start_workflow(
        WaitingForHandlersWorkflow.run,
        WorkflowInput(exit_type=exit_type),
        id=WORKFLOW_ID,
        task_queue=TASK_QUEUE,
        id_conflict_policy=common.WorkflowIDConflictPolicy.TERMINATE_EXISTING,
    )
    await _check_run(wf_handle, exit_type)


async def _check_run(
    wf_handle: client.WorkflowHandle,
    exit_type: WorkflowExitType,
):
    try:
        up_handle = await wf_handle.start_update(
            WaitingForHandlersWorkflow.my_update,
            wait_for_stage=client.WorkflowUpdateStage.ACCEPTED,
        )
    except Exception as e:
        print(f"    🔴 caught exception while starting update: {e}: {e.__cause__ or ''}")

    if exit_type == WorkflowExitType.CANCELLATION:
        await wf_handle.cancel()

    try:
        await up_handle.result()
        print("    🟢 caller received update result")
    except Exception as e:
        print(
            f"    🔴 caught exception while waiting for update result: {e}: {e.__cause__ or ''}"
        )

    try:
        await wf_handle.result()
        print("    🟢 caller received workflow result")
    except BaseException as e:
        print(
            f"    🔴 caught exception while waiting for workflow result: {e}: {e.__cause__ or ''}"
        )


async def main():
    for exit_type in [
        WorkflowExitType.SUCCESS,
        WorkflowExitType.FAILURE,
        WorkflowExitType.CANCELLATION,
    ]:
        print(f"\n\nworkflow exit type: {exit_type.name}")
        await starter(exit_type)


if __name__ == "__main__":
    asyncio.run(main())
