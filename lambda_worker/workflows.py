from datetime import timedelta

from temporalio import common, workflow
from temporalio.common import RetryPolicy

TASK_QUEUE = "keynote-demo"

with workflow.unsafe.imports_passed_through():
    from activities import hello_activity, process_vote_activity


@workflow.defn(versioning_behavior=common.VersioningBehavior.AUTO_UPGRADE)
class SampleWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        workflow.logger.info("SampleWorkflow started with name: %s", name)
        result = await workflow.execute_activity(
            hello_activity,
            name,
            start_to_close_timeout=timedelta(seconds=180),
            heartbeat_timeout=timedelta(seconds=20),
        )
        workflow.logger.info("SampleWorkflow completed with result: %s", result)
        return result

@workflow.defn(versioning_behavior=common.VersioningBehavior.AUTO_UPGRADE)
class VoteProcessingWorkflow:
    @workflow.run
    async def run(self, label: str) -> dict:
        workflow.logger.info("VoteProcessingWorkflow started with label: %s", label)
        result = await workflow.execute_activity(
            process_vote_activity,
            label,
            start_to_close_timeout=timedelta(seconds=30),
            heartbeat_timeout=timedelta(seconds=5),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=5),
            ),
        )
        workflow.logger.info("VoteProcessingWorkflow completed with result: %s", result)
        return result
