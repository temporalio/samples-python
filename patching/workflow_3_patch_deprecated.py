from temporalio import workflow


@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self) -> None:
        workflow.deprecate_patch("my-patch")
        self._result = "post-patch"

    @workflow.query
    def result(self) -> str:
        return self._result
