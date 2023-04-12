import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

with workflow.unsafe.imports_passed_through():
    from activities import compose_greeting
    from obj import ComposeGreetingInput


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
        polling_interval = 5  # seconds
        max_poll_attempts = 10
        activities = workflow.execute_activity(
            compose_greeting,
            ComposeGreetingInput("Hello", name),
            start_to_close_timeout=timedelta(seconds=4),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=polling_interval),
                maximum_attempts=max_poll_attempts,
            ),
        )

        for i in range(max_poll_attempts):
            try:
                result = await activities
                return result
            except ActivityError:
                print(f"Activity failed, retrying in {polling_interval} seconds")

            await asyncio.sleep(polling_interval)

            if i % 3 == 0:  # every 3rd iteration
                workflow.continue_as_new(ChildWorkflow)

        # If we've reached here, it means all attempts failed
        raise Exception("Polling failed after all attempts")
