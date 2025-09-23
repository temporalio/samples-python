from datetime import timedelta
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from .activities import failing_activity, complex_failing_activity


@workflow.defn
class MultilineLoggingWorkflow:
    @workflow.run
    async def run(self, test_type: str) -> str:
        if test_type == "activity_exception":
            return await workflow.execute_activity(
                failing_activity,
                True,
                schedule_to_close_timeout=timedelta(seconds=5)
            )
        elif test_type == "complex_activity_exception":
            return await workflow.execute_activity(
                complex_failing_activity,
                schedule_to_close_timeout=timedelta(seconds=5)
            )
        elif test_type == "workflow_exception":
            raise RuntimeError(
                "Workflow exception with\nmultiple lines\nof error text"
            )
        else:
            return "No exception test"
