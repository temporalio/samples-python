import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

with workflow.unsafe.imports_passed_through():
    from activities import compose_greeting, ComposeGreetingInput


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
        attempt = 0
        for i in range(10):
            try:
                polling_activities = await workflow.execute_activity(
                    compose_greeting,
                    ComposeGreetingInput("Hello", name),
                    start_to_close_timeout=timedelta(seconds=4),
                    retry_policy=RetryPolicy(
                        maximum_attempts=1,
                    ),
                )
                attempt += 1
                return polling_activities

            except ActivityError:
                workflow.logger.error("Activity failed, retrying in 5 seconds")
            await asyncio.sleep(5)

            workflow.continue_as_new(name)
        # If we've reached here, it means all attempts failed
        raise Exception("Polling failed after all attempts")
