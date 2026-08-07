from datetime import timedelta

from temporalio import workflow

TASK_QUEUE = "cloud-run-task-queue"

with workflow.unsafe.imports_passed_through():
    from cloud_run_worker.activities import hello_activity


@workflow.defn
class SampleWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        workflow.logger.info("SampleWorkflow started with name: %s", name)
        result = await workflow.execute_activity(
            hello_activity,
            name,
            start_to_close_timeout=timedelta(seconds=10),
        )
        workflow.logger.info("SampleWorkflow completed with result: %s", result)
        return result
