from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from worker_versioning.activities import greet, super_greet


@workflow.defn
class MyWorkflow:
    """
    The 1.1 version of the workflow, which is compatible with the first version.

    The compatible changes we've made are:
      - Altering the log lines
      - Using the `patched` API to properly introduce branching behavior while maintaining
        compatibility
    """

    should_finish: bool = False

    @workflow.run
    async def run(self) -> str:
        workflow.logger.info("Running workflow V1.1")
        await workflow.wait_condition(lambda: self.should_finish)
        return "Concluded workflow on V1.1"

    @workflow.signal
    def proceeder(self, inp: str):
        if workflow.patched("different-activity"):
            await workflow.execute_activity(super_greet, ["V1.1", 100])
        else:
            # Note it is a valid compatible change to alter the input to an activity. However, because
            # we're using the patched API, this branch would only be taken if the workflow was started on
            # a v1 worker.
            await workflow.execute_activity(greet, "V1.1")

        if inp == "finish":
            self.should_finish = True
