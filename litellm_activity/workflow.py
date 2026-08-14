from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

from litellm_activity.shared import LLMRequest

with workflow.unsafe.imports_passed_through():
    from litellm_activity.activities import call_litellm


@workflow.defn
class LiteLLMWorkflow:
    @workflow.run
    async def run(self, request: LLMRequest) -> str:
        return await workflow.execute_activity(
            call_litellm,
            request,
            start_to_close_timeout=timedelta(seconds=45),
            schedule_to_close_timeout=timedelta(minutes=2),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=10),
                maximum_attempts=3,
            ),
        )
