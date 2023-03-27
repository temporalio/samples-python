from temporalio import workflow


@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self) -> None:
        if workflow.patched("my-patch"):
            self._result = "post-patch"
        else:
            self._result = "pre-patch"

    @workflow.query
    def result(self) -> str:
        return self._result
