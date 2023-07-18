import asyncio

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from worker_versioning.activities import greet


@workflow.defn
class MyWorkflow:
    """
    The 2.0 version of the workflow, which is fully incompatible with the other workflows, since it
    alters the sequence of commands without using `patched`.
    """

    should_finish: bool = False

    @workflow.run
    async def run(self) -> str:
        workflow.logger.info("Running workflow V2")
        await workflow.wait_condition(lambda: self.should_finish)
        return "Concluded workflow on V2"

    @workflow.signal
    def proceeder(self, inp: str):
        await asyncio.sleep(1)
        await workflow.execute_activity(greet, "V2")
        await workflow.execute_activity(greet, "V2")

        if inp == "finish":
            self.should_finish = True
