from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    from reqrespupdate.activities import uppercase


# Error type used when the workflow rejects a request because it is continuing
# as new. The requester matches on this to tell "back off and retry" apart from
# a genuine failure.
BACKOFF_ERROR_TYPE = "ContinuingAsNew"


# Be in the habit of storing message inputs and outputs in serializable
# structures. This makes it easier to add more over time in a
# backward-compatible way.
@dataclass
class Request:
    input: str


@dataclass
class Response:
    output: str


@dataclass
class UppercaseWorkflowInput:
    # Workflows cannot have infinitely-sized history, so a workflow that fields
    # requests forever has to continue-as-new periodically. We bound the number
    # of requests each run accepts.
    requests_before_continue_as_new: int = 500
    # If requests arrive faster than they are handled, the workflow may never
    # get an idle moment in which to continue-as-new, and history keeps growing.
    # Rejecting requests from the update validator while a continue-as-new is
    # pending gives the workflow that idle moment and tells the requester to
    # back off. A validator rejection is not written to history, which is what
    # makes it a useful tool when the problem is history size.
    reject_update_on_pending_continue_as_new: bool = True


@workflow.defn
class UppercaseWorkflow:
    """A long-running workflow that uppercases strings on request.

    The response is returned directly from the update handler, so there is no
    response task queue, no callback activity and no request IDs to correlate.
    """

    @workflow.init
    def __init__(self, input: UppercaseWorkflowInput) -> None:
        # A run has to accept at least one request, otherwise it continues as
        # new the moment it starts and the chain never does any work.
        if input.requests_before_continue_as_new < 1:
            raise ApplicationError(
                "requests_before_continue_as_new must be at least 1",
                non_retryable=True,
            )
        self.input = input
        self.request_count = 0

    @workflow.run
    async def run(self, input: UppercaseWorkflowInput) -> None:
        # Wait until this run has taken its share of requests and no handler is
        # still running. all_handlers_finished() accounts for in-flight update
        # handlers, including ones waiting on an activity retry, so there is no
        # need to track pending handlers by hand.
        await workflow.wait_condition(
            lambda: self.continue_as_new_pending() and workflow.all_handlers_finished()
        )
        workflow.continue_as_new(input)

    @workflow.update
    async def uppercase(self, request: Request) -> Response:
        self.request_count += 1
        # WARNING: the timeout and retry policy affect how long this handler can
        # stay in flight, and therefore how long the workflow can be prevented
        # from continuing as new. Set them balancing resilience against the need
        # for a period of idleness.
        output = await workflow.execute_activity(
            uppercase,
            request.input,
            schedule_to_close_timeout=timedelta(seconds=5),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )
        return Response(output=output)

    @uppercase.validator
    def validate_uppercase(self, request: Request) -> None:
        # Raising from a validator rejects the update without writing it to
        # history, and without the workflow having to handle it. Note that a
        # validator must be synchronous.
        if (
            self.input.reject_update_on_pending_continue_as_new
            and self.continue_as_new_pending()
        ):
            raise ApplicationError(
                "Workflow is continuing as new, please retry",
                type=BACKOFF_ERROR_TYPE,
            )

    def continue_as_new_pending(self) -> bool:
        return self.request_count >= self.input.requests_before_continue_as_new
