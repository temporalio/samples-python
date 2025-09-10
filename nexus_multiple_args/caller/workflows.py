from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from nexus_multiple_args.service import HelloInput, Language, MyNexusService

NEXUS_ENDPOINT = "nexus-multiple-args-nexus-endpoint"


# This is a workflow that calls a nexus operation with multiple arguments.
@workflow.defn
class CallerWorkflow:
    # An __init__ method is always optional on a workflow class. Here we use it to set the
    # nexus client, but that could alternatively be done in the run method.
    def __init__(self):
        self.nexus_client = workflow.create_nexus_client(
            service=MyNexusService,
            endpoint=NEXUS_ENDPOINT,
        )

    # The workflow run method demonstrates calling a nexus operation with multiple arguments
    # packed into an input object.
    @workflow.run
    async def run(self, name: str, language: Language) -> str:
        # Start the nexus operation and wait for the result in one go, using execute_operation.
        # The multiple arguments (name and language) are packed into a HelloInput object.
        result = await self.nexus_client.execute_operation(
            MyNexusService.hello,
            HelloInput(name=name, language=language),
        )
        return result.message
