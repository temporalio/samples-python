import asyncio
from datetime import timedelta

from temporalio import exceptions, workflow

from message_passing.waiting_for_handlers import (
    WorkflowExitType,
    WorkflowInput,
    WorkflowResult,
)
from message_passing.waiting_for_handlers.activities import (
    activity_executed_by_update_handler,
)


def is_workflow_exit_exception(e: BaseException) -> bool:
    """
    True if the exception is of a type that will cause the workflow to exit.

    This is as opposed to exceptions that cause a workflow task failure, which
    are retried automatically by Temporal.
    """
    # 👉 If you have set additional failure_exception_types you should also
    # check for these here.
    return isinstance(e, (asyncio.CancelledError, exceptions.FailureError))


@workflow.defn
class WaitingForHandlersWorkflow:
    @workflow.run
    async def run(self, input: WorkflowInput) -> WorkflowResult:
        """
        This workflow.run method demonstrates a pattern that can be used to wait for signal and
        update handlers to finish in the following circumstances:

        - On successful workflow return
        - On workflow cancellation
        - On workflow failure

        Your workflow can also exit via Continue-As-New. In that case you would usually wait for
        the handlers to finish immediately before the call to continue_as_new(); that's not
        illustrated in this sample.

        If you additionally need to perform cleanup or compensation on workflow failure or
        cancellation, see the message_passing/waiting_for_handlers_and_compensation sample.
        """
        try:
            # 👉 Use this `try...except` style, instead of waiting for message
            # handlers to finish in a `finally` block. The reason is that some
            # exception types cause a workflow task failure as opposed to
            # workflow exit, in which case we do *not* want to wait for message
            # handlers to finish.
            result = await self._my_workflow_application_logic(input)
            await workflow.wait_condition(workflow.all_handlers_finished)
            return result
        # 👉 Catch BaseException since asyncio.CancelledError does not inherit
        # from Exception.
        except BaseException as e:
            if is_workflow_exit_exception(e):
                await workflow.wait_condition(workflow.all_handlers_finished)
            raise

    # Methods below this point can be ignored unless you are interested in
    # the implementation details of this sample.

    def __init__(self) -> None:
        self._update_started = False

    @workflow.update
    async def my_update(self) -> str:
        self._update_started = True
        await workflow.execute_activity(
            activity_executed_by_update_handler,
            start_to_close_timeout=timedelta(seconds=10),
        )
        return "update-result"

    async def _my_workflow_application_logic(
        self, input: WorkflowInput
    ) -> WorkflowResult:
        # The main workflow logic is implemented in a separate method in order
        # to separate "platform-level" concerns (waiting for handlers to finish
        # and error handling) from application logic.

        # Wait until handlers have started, so that we are demonstrating that we
        # wait for them to finish.
        await workflow.wait_condition(lambda: self._update_started)
        if input.exit_type == WorkflowExitType.SUCCESS:
            return WorkflowResult(data="workflow-result")
        elif input.exit_type == WorkflowExitType.FAILURE:
            raise exceptions.ApplicationError("deliberately failing workflow")
        elif input.exit_type == WorkflowExitType.CANCELLATION:
            # Block forever; the starter will send a workflow cancellation request.
            await asyncio.Future()
        raise AssertionError("unreachable")
