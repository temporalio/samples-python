from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from worker_versioning.activities import greet


@workflow.defn
class MyWorkflow:
    """The 1.0 version of the workflow we'll be making changes to"""

    should_finish: bool = False

    @workflow.run
    async def run(self) -> str:
        workflow.logger.info("Running workflow V1")
        await workflow.wait_condition(lambda: self.should_finish)
        return "Concluded workflow on V1"

    @workflow.signal
    async def proceeder(self, inp: str):
        await workflow.execute_activity(
            greet, "V1", start_to_close_timeout=timedelta(seconds=5)
        )
        if inp == "finish":
            self.should_finish = True
