from temporalio import workflow
from temporalio.workflow import NexusClient

with workflow.unsafe.imports_passed_through():
    from hello_nexus.basic.service import MyInput, MyNexusService, MyOutput

NEXUS_ENDPOINT = "my-nexus-endpoint"


# This is a workflow that calls a nexus operation.
@workflow.defn
class CallerWorkflow:
    # An __init__ method is always optional on a Workflow class. Here we use it to set the
    # NexusClient, but that could alternatively be done in the run method.
    def __init__(self):
        self.nexus_client = NexusClient(
            MyNexusService,
            endpoint=NEXUS_ENDPOINT,
        )

    # The Wokflow run method invokes two Nexus operations.
    @workflow.run
    async def run(self, name: str) -> tuple[MyOutput, MyOutput]:
        # Start the Nexus operation and wait for the result in one go, using execute_operation.
        wf_result = await self.nexus_client.execute_operation(
            MyNexusService.my_workflow_run_operation,
            MyInput(name),
        )
        # We could use execute_operation for this one also, but here we demonstrate
        # obtaining the operation handle and then using it to get the result.
        sync_operation_handle = await self.nexus_client.start_operation(
            MyNexusService.my_sync_operation,
            MyInput(name),
        )
        sync_result = await sync_operation_handle
        return sync_result, wf_result
