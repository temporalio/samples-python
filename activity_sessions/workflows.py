from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

from activity_sessions.models import (
    ACTIVITY_NAME,
    ConversationRequest,
    StepInput,
    StepResult,
)


@workflow.defn
class ProcessConversation:
    @workflow.run
    async def run(self, request: ConversationRequest) -> list[StepResult]:
        if request.steps < 1:
            raise ApplicationError(
                "At least one conversation step is required", non_retryable=True
            )
        session_options = (
            workflow.ActivitySessionOptions.workflow_session()
            if request.affinity_enabled
            else None
        )
        input_ref = request.input_ref
        results = []
        for step in range(1, request.steps + 1):
            result = await workflow.execute_activity(
                ACTIVITY_NAME,
                StepInput(step=step, input_ref=input_ref),
                result_type=StepResult,
                session_options=session_options,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=1),
            )
            results.append(result)
            input_ref = result.output_ref
        return results
