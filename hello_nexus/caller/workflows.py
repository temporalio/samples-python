from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from hello_nexus.service import MyInput, MyNexusService, MyOutput

NEXUS_ENDPOINT = "hello-nexus-basic-nexus-endpoint"


# This is a workflow that calls two nexus operations.
@workflow.defn
class CallerWorkflow:
    # An __init__ method is always optional on a workflow class. Here we use it to set the
    # nexus client, but that could alternatively be done in the run method.
    def __init__(self):
        self.nexus_client = workflow.create_nexus_client(
            service=MyNexusService,
            endpoint=NEXUS_ENDPOINT,
        )

    # The workflow run method invokes two nexus operations.
    @workflow.run
    async def run(self, name: str) -> tuple[MyOutput, MyOutput]:
        # Start the nexus operation and wait for the result in one go, using execute_operation.
        op_1_result = await self.nexus_client.execute_operation(
            MyNexusService.my_sync_operation,
            MyInput(name),
        )
        # Alternatively, you can use start_operation to obtain the operation handle and
        # then `await` the handle to obtain the result.
        op_2_handle = await self.nexus_client.start_operation(
            MyNexusService.my_workflow_run_operation,
            MyInput(name),
        )
        op_2_result = await op_2_handle
        return op_1_result, op_2_result
