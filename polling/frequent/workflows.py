from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from polling.frequent.activities import ComposeGreetingInput, compose_greeting


@workflow.defn
class GreetingWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        return await workflow.execute_activity(
            compose_greeting,
            ComposeGreetingInput("Hello", name),
            start_to_close_timeout=timedelta(seconds=60),
            heartbeat_timeout=timedelta(seconds=2),
        )
