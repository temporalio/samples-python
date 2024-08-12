import asyncio

from temporalio import workflow
from temporalio.client import WorkflowUpdateStage
from utils import catch, start_workflow


@workflow.defn
class Workflow:
    @workflow.run
    async def run(self) -> str:
        await workflow.wait_condition(lambda: False)
        return "workflow-result"

    @workflow.query
    def my_query(self) -> str:
        # assert False
        return "query-result"

    @workflow.signal
    async def my_signal(self):
        pass

    @workflow.update
    async def my_update(self) -> str:
        # await asyncio.sleep(5)
        # assert False
        return "update-result"


async def main():
    wf_handle = await start_workflow(Workflow.run)

    print("waiting for update acceptance...")
    with catch():
        update_handle = await wf_handle.start_update(
            Workflow.my_update, wait_for_stage=WorkflowUpdateStage.ACCEPTED
        )
    print("waiting for update result...")
    with catch():
        print("update result:", await update_handle.result())

    print("workflow result:", await wf_handle.result())


if __name__ == "__main__":
    asyncio.run(main())
