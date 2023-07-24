from temporalio import activity, workflow
from dataclasses import dataclass
from datetime import timedelta
# Import our activity and param class, passing it through the sandbox
with workflow.unsafe.imports_passed_through():
    from sentry.activities import ComposeGreetingInput, compose_greeting


@workflow.defn
class GreetingWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        workflow.logger.info("Running workflow with parameter %s" % name)
        return await workflow.execute_activity(
            compose_greeting,
            ComposeGreetingInput("Hello", name),
            start_to_close_timeout=timedelta(seconds=10),
        )
