from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from polling.infrequent.activities import ComposeGreeting, ComposeGreetingInput


@workflow.defn
class GreetingWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        return await workflow.execute_activity_method(
            ComposeGreeting.compose_greeting,
            ComposeGreetingInput("Hello", name),
            start_to_close_timeout=timedelta(seconds=2),
            retry_policy=RetryPolicy(
                backoff_coefficient=1.0,
                initial_interval=timedelta(seconds=60),
            ),
        )
