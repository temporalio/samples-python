import asyncio

from temporalio import client

from message_passing.message_handler_waiting_compensation_cleanup import (
    TASK_QUEUE,
    WORKFLOW_ID,
    OnWorkflowExitAction,
    UpdateInput,
    WorkflowExitType,
    WorkflowInput,
)
from message_passing.message_handler_waiting_compensation_cleanup.workflows import (
    MyWorkflow,
)


async def starter(exit_type: WorkflowExitType, update_action: OnWorkflowExitAction):
    cl = await client.Client.connect("localhost:7233")
    wf_handle = await cl.start_workflow(
        MyWorkflow.run,
        WorkflowInput(exit_type=exit_type),
        id=WORKFLOW_ID,
        task_queue=TASK_QUEUE,
    )
    await _check_run(wf_handle, exit_type, update_action)


async def _check_run(
    wf_handle: client.WorkflowHandle,
    exit_type: WorkflowExitType,
    update_action: OnWorkflowExitAction,
):
    try:
        up_handle = await wf_handle.start_update(
            MyWorkflow.my_update,
            UpdateInput(on_premature_workflow_exit=update_action),
            wait_for_stage=client.WorkflowUpdateStage.ACCEPTED,
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
        await _check_run(wf_handle, WorkflowExitType.SUCCESS, update_action)
    else:
        try:
            await wf_handle.result()
            print("    🟢 caller received workflow result")
        except Exception as e:
            print(
                f"    🔴 caught exception while waiting for workflow result: {e}: {e.__cause__ or ''}"
            )


async def main():
    for exit_type in WorkflowExitType:
        print(f"\n\nworkflow exit type: {exit_type.name}")
        for update_action in [
            OnWorkflowExitAction.CONTINUE,
            OnWorkflowExitAction.ABORT_WITH_COMPENSATION,
        ]:
            print(f"  update action on premature workflow exit: {update_action}")
            await starter(exit_type, update_action)


if __name__ == "__main__":
    asyncio.run(main())
