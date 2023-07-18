from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from your_activities import your_activity
    from your_dataobject import YourParams


@workflow.defn
class YourSchedulesWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        return await workflow.execute_activity(
            your_activity,
            YourParams("Hello", name),
            start_to_close_timeout=timedelta(seconds=10),
        )
