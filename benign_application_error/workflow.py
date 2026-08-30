from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from benign_application_error.activities import greeting_activities

@workflow.defn
class BenignApplicationErrorWorkflow:
    @workflow.run
    async def run(self, use_benign: bool) -> None:
        await workflow.execute_activity(
            greeting_activities,
            use_benign,
            start_to_close_timeout=timedelta(seconds=5),
            schedule_to_close_timeout=timedelta(seconds=5),
            retry_policy=RetryPolicy(maximum_attempts=1),
        )
