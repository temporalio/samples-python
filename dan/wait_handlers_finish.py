import asyncio
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum

from temporalio import activity, client, common, exceptions, workflow

TASK_QUEUE = "tq"
WORKFLOW_ID = "wid"


class TerminationType(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    CONTINUE_AS_NEW = "continue_as_new"
    CANCELLATION = "cancellation"


@dataclass
class WorkflowInput:
    termination_type: TerminationType


@workflow.defn
class Workflow:
    """
    This Workflow upholds the following recommended practices:

    1. The main workflow method ensures that all signal and update handlers are
       finished before a successful return, and on failure, cancellation, and
       continue-as-new.
    2. The update handler performs any necessary compensation/cleanup when the
       workflow is cancelled, fails, or continues-as-new.
    """

    def __init__(self) -> None:
        self.workflow_exit_exception: asyncio.Future[BaseException] = asyncio.Future()

    @workflow.run
    async def run(self, input: WorkflowInput) -> str:
        try:
            # 👉 Use this `try...except` style, instead of waiting for message
            # handlers to finish in a `finally` block. The reason is that other
            # exception types will cause a Workflow Task failure, in which case
            # we do *not* want to wait for message handlers to finish.
            result = await self._run(input)
            await workflow.wait_condition(workflow.all_handlers_finished)
            return result
        except (
            asyncio.CancelledError,
            workflow.ContinueAsNewError,
            exceptions.FailureError,
        ) as exc:
            self.workflow_exit_exception.set_result(exc)
            await workflow.wait_condition(workflow.all_handlers_finished)
            raise exc

    @workflow.update
    async def my_update(self) -> str:
        """
        This update handler demonstrates how to handle the situation where the
        main Workflow method exits prematurely. In that case we perform
        compensation/cleanup, and fail the Update. The Update caller will get a
        WorkflowUpdateFailedError.
        """
        # Coroutines must be wrapped in tasks in order to use workflow.wait.
        update_task = asyncio.Task(self._my_update())
        # 👉 Always use `workflow.wait` instead of `asyncio.wait` in Workflow
        # code: asyncio's version is non-deterministic.
        first_completed, _ = await workflow.wait(
            [update_task, self.workflow_exit_exception],
            return_when=asyncio.FIRST_COMPLETED,
        )
        # 👉 It's possible that the update completed and the workflow exited
        # prematurely in the same tick of the event loop. If the Update has
        # completed, return the Update result to the caller, whether or not the
        # Workflow is exiting.
        if update_task in first_completed:
            return await update_task
        else:
            await self._my_update_compensation_and_cleanup()
            raise exceptions.ApplicationError(
                f"The update failed because the workflow run exited: {await self.workflow_exit_exception}"
            )

    async def _my_update(self) -> str:
        """
        This handler is slow, so will result in an
        UnfinishedUpdateHandlersWarning (TMPRL1102) unless the main workflow
        task waits for it to finish.
        """
        # Ignore: implementation detail specific to this sample
        self._update_started = True

        await workflow.execute_activity(
            my_activity, start_to_close_timeout=timedelta(seconds=10)
        )
        return "update-result"

    async def _my_update_compensation_and_cleanup(self):
        print("    performing update handler compensation and cleanup operations")

    async def _run(self, input: WorkflowInput) -> str:
        """
        Ignore this method unless you are interested in the implementation
        details of this sample.

        This method is not illustrating how to write workflow code; it is just
        doing what is necessary to demonstrate the points that this sample is
        demonstrating.
        """
        # Wait until handlers started, so that we are demonstrating that we wait for them to finish.
        await workflow.wait_condition(lambda: getattr(self, "_update_started", False))
        if input.termination_type == TerminationType.SUCCESS:
            return "workflow-result"
        elif input.termination_type == TerminationType.CONTINUE_AS_NEW:
            workflow.continue_as_new(
                WorkflowInput(termination_type=TerminationType.SUCCESS)
            )
        elif input.termination_type == TerminationType.FAILURE:
            raise exceptions.ApplicationError("deliberately failing workflow")
        elif input.termination_type == TerminationType.CANCELLATION:
            # Block forever; the starter will send a workflow cancellation request.
            await asyncio.Future()
        raise AssertionError("unreachable")


@activity.defn
async def my_activity():
    await asyncio.sleep(3)


async def starter():
    cl = await client.Client.connect("localhost:7233")

    for termination_type in [
        TerminationType.SUCCESS,
        # TerminationType.FAILURE,
        # TerminationType.CANCELLATION,
        # TerminationType.CONTINUE_AS_NEW,
    ]:
        print(f"\nstarting workflow with termination type: {termination_type}")
        wf_handle = await cl.start_workflow(
            Workflow.run,
            WorkflowInput(termination_type=termination_type),
            id=WORKFLOW_ID,
            task_queue=TASK_QUEUE,
            id_reuse_policy=common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
        )
        await _check_run(wf_handle, termination_type)


async def _check_run(
    wf_handle: client.WorkflowHandle, termination_type: TerminationType
):
    with catch("starting update"):
        up_handle = await wf_handle.start_update(
            Workflow.my_update, wait_for_stage=client.WorkflowUpdateStage.ACCEPTED
        )

    if termination_type == TerminationType.CANCELLATION:
        await wf_handle.cancel()

    with catch("waiting for update result"):
        await up_handle.result()
        print("    🟢 caller received update result")

    if termination_type == TerminationType.CONTINUE_AS_NEW:
        await _check_run(wf_handle, TerminationType.SUCCESS)
    else:
        with catch("waiting for workflow result"):
            await wf_handle.result()
            print("    🟢 caller received workflow result")


@contextmanager
def catch(operation: str):
    try:
        yield
    except Exception as e:
        print(f"    🔴 caught exception while {operation}:", e, file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(starter())
