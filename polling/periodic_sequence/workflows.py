import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

with workflow.unsafe.imports_passed_through():
    from polling.periodic_sequence.activities import compose_greeting
    from polling.test_service import ComposeGreetingInput


@workflow.defn
class GreetingWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        return await workflow.execute_child_workflow(
            ChildWorkflow.run,
            name,
        )


@workflow.defn
class ChildWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        for i in range(10):
            try:
                return await workflow.execute_activity(
                    compose_greeting,
                    ComposeGreetingInput("Hello", name),
                    start_to_close_timeout=timedelta(seconds=4),
                    retry_policy=RetryPolicy(
                        maximum_attempts=1,
                    ),
                )

            except ActivityError:
                workflow.logger.error("Activity failed, retrying in 1 seconds")
            await asyncio.sleep(1)
            workflow.continue_as_new(name)

        raise Exception("Polling failed after all attempts")
