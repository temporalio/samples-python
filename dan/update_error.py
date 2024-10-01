import asyncio
from typing import NoReturn

from temporalio import workflow
from temporalio.client import WorkflowUpdateFailedError, WorkflowUpdateStage
from temporalio.exceptions import FailureError

from dan.utils import start_workflow


@workflow.defn
class Workflow:
    def __init__(self):
        self.done = False

    @workflow.run
    async def run(self) -> NoReturn:
        await workflow.wait_condition(lambda: self.done)

    @workflow.update
    async def my_update(self) -> NoReturn:
        self.done = True
        raise FailureError("deliberate FailureError in update handler")


#        raise ApplicationError("deliberate ApplicationError in update handler")


async def main():
    wf_handle = await start_workflow(Workflow.run)
    upd_handle = await wf_handle.start_update(
        Workflow.my_update, wait_for_stage=WorkflowUpdateStage.ACCEPTED
    )
    try:
        print(f"Update Result: {await upd_handle.result()}")
    except WorkflowUpdateFailedError as e:
        print(f"Caught Update Error: {e.cause}")
    print(f"Workflow Result: {await wf_handle.result()}")


if __name__ == "__main__":
    asyncio.run(main())
