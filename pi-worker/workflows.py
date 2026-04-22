from datetime import timedelta

from temporalio import common, workflow

TASK_QUEUE = "tq-demo-order"

with workflow.unsafe.imports_passed_through():
    from activities import hello_activity


@workflow.defn(versioning_behavior=common.VersioningBehavior.AUTO_UPGRADE)
class SampleWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        workflow.logger.info("SampleWorkflow started with name: %s", name)
        result = await workflow.execute_activity(
            hello_activity,
            name,
            start_to_close_timeout=timedelta(seconds=180),
            heartbeat_timeout=timedelta(seconds=10),
        )
        workflow.logger.info("SampleWorkflow completed with result: %s", result)
        return result
