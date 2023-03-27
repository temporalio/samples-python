from temporalio import workflow


@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self) -> None:
        self._result = "pre-patch"

    @workflow.query
    def result(self) -> str:
        return self._result
