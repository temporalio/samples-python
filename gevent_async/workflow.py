from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from gevent_async.activity import (
        ComposeGreetingInput,
        compose_greeting_async,
        compose_greeting_sync,
    )


@workflow.defn
class GreetingWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        workflow.logger.info("Running workflow with parameter %s" % name)

        # Run an async and a sync activity
        async_res = await workflow.execute_activity(
            compose_greeting_async,
            ComposeGreetingInput("Hello", name),
            start_to_close_timeout=timedelta(seconds=10),
        )
        sync_res = await workflow.execute_activity(
            compose_greeting_sync,
            ComposeGreetingInput("Hello", name),
            start_to_close_timeout=timedelta(seconds=10),
        )

        # Confirm the same, return one
        if async_res != sync_res:
            raise ValueError("Results are not the same")
        return sync_res
