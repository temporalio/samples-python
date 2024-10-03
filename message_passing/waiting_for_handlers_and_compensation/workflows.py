import asyncio
from datetime import timedelta
from typing import cast

from temporalio import exceptions, workflow

from message_passing.waiting_for_handlers_and_compensation import (
    WorkflowExitType,
    WorkflowInput,
)
from message_passing.waiting_for_handlers_and_compensation.activities import (
    activity_executed_by_update_handler,
    activity_executed_by_update_handler_to_perform_compensation,
)


@workflow.defn
class WaitingForHandlersAndCompensationWorkflow:
    """
    This Workflow demonstrates how to wait for message handlers to finish and
    perform compensation/cleanup:

    1. It ensures that all signal and update handlers have finished before a
       successful return, and on failure, cancellation, and continue-as-new.
    2. The update handler performs any necessary compensation/cleanup when the
       workflow is cancelled, fails, or continues-as-new.
    """

    def __init__(self) -> None:
        # 👉 If the workflow exits prematurely, this future will be completed
        # with the associated exception as its value. Message handlers can then
        # "race" this future against a task performing the message handler's own
        # application logic; if this future completes before the message handler
        # task then the handler should abort and perform compensation.
        self.workflow_exit = asyncio.Future()

    @workflow.run
    async def run(self, input: WorkflowInput) -> str:
        try:
            # 👉 Use this `try...except` style, instead of waiting for message
            # handlers to finish in a `finally` block. The reason is that some
            # exception types cause a workflow task failure as opposed to
            # workflow exit, in which case we do *not* want to wait for message
            # handlers to finish.

            # 👉 self._run contains your actual application logic. This is
            # implemented in a separate method in order to separate
            # "platform-level" concerns (waiting for handlers to finish and
            # ensuring that compensation is performed when appropriate) from
            # application logic. In this sample, its actual implementation is
            # below but contains nothing relevant.
            result = await self._run(input)
            self.workflow_exit.set_result(None)
            await workflow.wait_condition(workflow.all_handlers_finished)
            return result
        # 👉 Catch BaseException since asyncio.CancelledError does not inherit
        # from Exception.
        except BaseException as e:
            if is_workflow_exit_exception(e):
                self.workflow_exit.set_exception(e)
                await workflow.wait_condition(workflow.all_handlers_finished)
            raise

    @workflow.update
    async def my_update(self) -> str:
        """
        An update handler that handles exceptions in itself and in the main
        workflow method.

        It ensures that:
        - Compensation/cleanup is always performed when appropriate
        - The update caller gets the update result, or WorkflowUpdateFailedError
        """
        # 👉 As with the main workflow method, the update application logic is
        # implemented in a separate method in order to separate "platform-level"
        # error-handling and compensation concerns from application logic. Note
        # that coroutines must be wrapped in tasks in order to use
        # workflow.wait.
        update_task = asyncio.create_task(self._my_update())

        # 👉 "Race" the workflow_exit future against the handler's own application
        # logic. Always use `workflow.wait` instead of `asyncio.wait` in
        # Workflow code: asyncio's version is non-deterministic.
        await workflow.wait(
            [update_task, self.workflow_exit], return_when=asyncio.FIRST_EXCEPTION
        )
        try:
            if update_task.done():
                # 👉 The update has finished (whether successfully or not).
                # Regardless of whether the main workflow method is about to
                # exit or not, the update caller should receive a response
                # informing them of the outcome of the update. So return the
                # result, or raise the exception that caused the update handler
                # to exit.
                return await update_task
            else:
                # 👉 The main workflow method exited prematurely due to an
                # error, and this happened before the update finished. Fail the
                # update with the workflow exception as cause.
                raise exceptions.ApplicationError(
                    "The update failed because the workflow run exited"
                ) from cast(BaseException, self.workflow_exit.exception())
        # 👉 Catch BaseException since asyncio.CancelledError does not inherit
        # from Exception.
        except BaseException as e:
            if is_workflow_exit_exception(e):
                try:
                    await self.my_update_compensation()
                except BaseException as e:
                    raise exceptions.ApplicationError(
                        "Update compensation failed"
                    ) from e
            raise

    async def my_update_compensation(self):
        await workflow.execute_activity(
            activity_executed_by_update_handler_to_perform_compensation,
            start_to_close_timeout=timedelta(seconds=10),
        )

    # The following two methods are placeholders for the actual application
    # logic that you would perform in your main workflow method  or update
    # handler. Their implementation can be ignored.

    async def _my_update(self) -> str:
        # Ignore this method unless you are interested in the implementation
        # details of this sample.
        self._update_started = True
        await workflow.execute_activity(
            activity_executed_by_update_handler,
            start_to_close_timeout=timedelta(seconds=10),
        )
        return "update-result"

    async def _run(self, input: WorkflowInput) -> str:
        # Ignore this method unless you are interested in the implementation
        # details of this sample.

        # Wait until handlers have started, so that we are demonstrating that we
        # wait for them to finish.
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


def is_workflow_exit_exception(e: BaseException) -> bool:
    # 👉 If you have set additional failure_exception_types you should also
    # check for these here.
    return isinstance(
        e,
        (asyncio.CancelledError, workflow.ContinueAsNewError, exceptions.FailureError),
    )
