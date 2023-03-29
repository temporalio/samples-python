from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from patching.activities import pre_patch_activity


@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self) -> None:
        self._result = await workflow.execute_activity(
            pre_patch_activity,
            schedule_to_close_timeout=timedelta(minutes=5),
        )

    @workflow.query
    def result(self) -> str:
        return self._result
