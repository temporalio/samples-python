import asyncio

from temporalio import workflow
from temporalio.client import WorkflowUpdateStage

from dan.utils import start_workflow


@workflow.defn
class Workflow:
    def __init__(self):
        self.is_complete = False

    @workflow.run
    async def run(self) -> None:
        print("In run")
        await workflow.wait_condition(lambda: self.is_complete)

    @workflow.update
    async def my_update(self) -> None:
        workflow.logger.info("In my_update")
        self.is_complete = True


async def main():
    handle = await start_workflow(Workflow.run)
    update_handle = await handle.start_update(
        Workflow.my_update, wait_for_stage=WorkflowUpdateStage.ACCEPTED
    )
    await update_handle.result()
    await handle.result()


if __name__ == "__main__":
    asyncio.run(main())
