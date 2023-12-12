from temporalio import workflow


@workflow.defn
class HelloWorldWorkflow:
    is_complete = False

    @workflow.run
    async def execute_workflow(self) -> str:
        await workflow.wait_condition(lambda: self.is_complete)
        return "Hello, World!"

    @workflow.update
    async def update_workflow_status(self) -> str:
        self.is_complete = True
        return "Workflow status updated"
