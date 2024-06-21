import asyncio
from datetime import timedelta
from temporalio import activity, workflow


with workflow.unsafe.imports_passed_through():
    from custom_converter.shared import GreetingInput, GreetingOutput


@workflow.defn
class GreetingWorkflow:
    @workflow.run
    async def run(self, input: GreetingInput) -> GreetingInput:
        return await workflow.execute_activity(
            compose_greeting,
            input,
            start_to_close_timeout=timedelta(seconds=10),
        )
        # return GreetingOutput(f"Hello, {input.name}")


@activity.defn
async def compose_greeting(input: GreetingInput) -> GreetingInput:
    # activity.logger.info("Running activity with parameter %s" % input)
    return GreetingInput(f"Hello, {input.name}")
