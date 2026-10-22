from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

from activity_sessions import StepResult


@workflow.defn
class ProcessConversation:
    @workflow.run
    async def run(self, affinity_enabled: bool) -> list[StepResult]:
        options: workflow.ActivityConfig = {
            "start_to_close_timeout": timedelta(seconds=30),
            "retry_policy": RetryPolicy(maximum_attempts=1),
            "session_options": (
                workflow.ActivitySessionOptions.workflow_session()
                if affinity_enabled
                else None
            ),
        }
        first = await workflow.execute_activity(
            "conversation_step", 1, result_type=StepResult, **options
        )
        second = await workflow.execute_activity(
            "conversation_step", 2, result_type=StepResult, **options
        )
        third = await workflow.execute_activity(
            "conversation_step", 3, result_type=StepResult, **options
        )
        return [first, second, third]
