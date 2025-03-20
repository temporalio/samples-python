import asyncio
import uuid

from temporalio import workflow
from temporalio.client import WorkflowUpdateStage

from dan.utils.client import start_workflow

failed = set()


@workflow.defn
class Workflow:
    def __init__(self):
        self.is_complete = False

    @workflow.run
    async def run(self) -> str:
        global failed
        wid = workflow.info().workflow_id
        if wid not in failed:
            failed.add(wid)
            raise Exception("Fail WFT")
        else:
            failed.remove(wid)

        await workflow.wait_condition(lambda: self.is_complete)
        return "workflow-result"

    @workflow.update
    async def my_update(self) -> str:
        self.is_complete = True
        return "update-result"


async def main():
    handle = await start_workflow(Workflow.run, id=str(uuid.uuid4()))
    update_handle = await handle.start_update(
        Workflow.my_update, wait_for_stage=WorkflowUpdateStage.ACCEPTED
    )
    update_result = await update_handle.result()
    print(f"Update Result: {update_result}")
    result = await handle.result()
    print(f"Workflow Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
