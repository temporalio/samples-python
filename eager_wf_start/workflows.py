from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from eager_wf_start.activities import greeting


@workflow.defn
class EagerWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        return await workflow.execute_local_activity(
            greeting, name, schedule_to_close_timeout=timedelta(seconds=5)
        )
