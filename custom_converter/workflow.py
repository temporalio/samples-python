from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from custom_converter.shared import GreetingInput, GreetingOutput


@workflow.defn
class GreetingWorkflow:
    @workflow.run
    async def run(self, input: GreetingInput) -> GreetingOutput:
        return GreetingOutput(f"Hello, {input.name}")
