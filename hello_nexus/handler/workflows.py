from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from hello_nexus.service import MyInput, MyOutput


# This is the workflow that is started by the `my_workflow_run_operation` nexus operation.
@workflow.defn
class WorkflowStartedByNexusOperation:
    @workflow.run
    async def run(self, input: MyInput) -> MyOutput:
        return MyOutput(message=f"Hello {input.name} from workflow run operation!")
