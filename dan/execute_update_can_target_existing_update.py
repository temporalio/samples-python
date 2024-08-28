import asyncio
from typing import NoReturn

from temporalio import workflow
from temporalio.client import WorkflowUpdateStage

from dan.utils import start_workflow

wid = __file__


@workflow.defn
class Workflow:
    def __init__(self):
        self.is_complete = False

    @workflow.run
    async def run(self) -> NoReturn:
        # workflow must stay alive in order to fetch update result
        await workflow.wait_condition(lambda: False)

    @workflow.update
    async def my_update(self) -> str:
        return "update result"


async def main():
    wf_handle = await start_workflow(Workflow.run, id=wid)
    upd_handle = await wf_handle.start_update(
        Workflow.my_update, wait_for_stage=WorkflowUpdateStage.ACCEPTED
    )
    print(f"Update Handle: {upd_handle}")
    result = await wf_handle.execute_update(Workflow.my_update, id=upd_handle.id)
    print(f"Update Result: {result}")
    print(f"Workflow Result: {await wf_handle.result()}")


if __name__ == "__main__":
    asyncio.run(main())
