import asyncio
from datetime import timedelta

from temporalio import exceptions, workflow

from message_passing.message_handler_waiting_compensation_cleanup import (
    OnWorkflowExitAction,
    UpdateInput,
    WorkflowExitType,
    WorkflowInput,
)
from message_passing.message_handler_waiting_compensation_cleanup.activities import (
    my_activity,
)


@workflow.defn
class MyWorkflow:
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
    async def my_update(self, input: UpdateInput) -> str:
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
        if (
            update_task in first_completed
            or input.on_premature_workflow_exit == OnWorkflowExitAction.CONTINUE
        ):
            return await update_task
        else:
            await self._my_update_compensation_and_cleanup()
            raise exceptions.ApplicationError(
                f"The update failed because the workflow run exited: {await self.workflow_exit_exception}"
            )

    async def _my_update(self) -> str:
        """
        This handler calls a slow activity, so

        (1) In the case where the workflow finishes successfully, the worker
            would get an UnfinishedUpdateHandlersWarning (TMPRL1102) if the main
            workflow task didn't wait for it to finish.

        (2) In the other cases (failure, cancellation, and continue-as-new), the
            premature workflow exit will occur before the update is finished.
        """
        # Ignore: implementation detail specific to this sample
        self._update_started = True

        await workflow.execute_activity(
            my_activity, start_to_close_timeout=timedelta(seconds=10)
        )
        return "update-result"

    async def _my_update_compensation_and_cleanup(self):
        workflow.logger.info(
            "performing update handler compensation and cleanup operations"
        )

    async def _run(self, input: WorkflowInput) -> str:
        # Ignore this method unless you are interested in the implementation
        # details of this sample.

        # Wait until handlers started, so that we are demonstrating that we wait for them to finish.
        await workflow.wait_condition(lambda: getattr(self, "_update_started", False))
        if input.exit_type == WorkflowExitType.SUCCESS:
            return "workflow-result"
        elif input.exit_type == WorkflowExitType.CONTINUE_AS_NEW:
            workflow.continue_as_new(WorkflowInput(exit_type=WorkflowExitType.SUCCESS))
        elif input.exit_type == WorkflowExitType.FAILURE:
            raise exceptions.ApplicationError("deliberately failing workflow")
        elif input.exit_type == WorkflowExitType.CANCELLATION:
            # Block forever; the starter will send a workflow cancellation request.
            await asyncio.Future()
        raise AssertionError("unreachable")
