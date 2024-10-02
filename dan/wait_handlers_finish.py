import asyncio
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum

from temporalio import client, common, exceptions, workflow

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
    This Workflow satisfies the following, all of which are recommended:

    1. The main workflow method ensures that all signal and update handlers are
       finished before a successful return, and on failure, cancellation, and
       continue-as-new.
    2. TODO: The update handler performs cleanup when the workflow is cancelled
       or fails.
    """

    def __init__(self) -> None:
        self.in_progress_message_handlers_should_abort_and_cleanup = asyncio.Event()

    @workflow.run
    async def run(self, input: WorkflowInput) -> str:
        try:
            result = await self._run(input)
            await workflow.wait_condition(workflow.all_handlers_finished)
            return result
        except (
            asyncio.CancelledError,
            workflow.ContinueAsNewError,
            exceptions.FailureError,
        ) as exc:
            await workflow.wait_condition(workflow.all_handlers_finished)
            raise exc

    @workflow.update
    async def my_update(self) -> str:
        self._update_started = True

        update_task = asyncio.Task(self._my_update())
        abort_task = asyncio.Task(
            self.in_progress_message_handlers_should_abort_and_cleanup.wait()
        )
        done, _ = await workflow.wait(
            [update_task, abort_task], return_when=asyncio.FIRST_COMPLETED
        )
        if abort_task in done:
            await self._my_update_cleanup()
            raise exceptions.ApplicationError(
                "The update failed because the workflow run was aborted"
            )

    async def _my_update(self) -> str:
        """
        This handler is slow, so will result in an
        UnfinishedUpdateHandlersWarning (TMPRL1102) unless the main workflow
        task waits for it to finish.
        """
        await asyncio.sleep(3)
        return "update-result"

    async def _my_update_cleanup(self):
        print("performing update handler cleanup operations")

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


async def starter():
    cl = await client.Client.connect("localhost:7233")

    for termination_type in [
        TerminationType.SUCCESS,
        TerminationType.FAILURE,
        TerminationType.CANCELLATION,
        TerminationType.CONTINUE_AS_NEW,
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
