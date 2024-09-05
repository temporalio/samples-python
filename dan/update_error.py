import asyncio
from typing import NoReturn

from temporalio import workflow
from temporalio.client import WorkflowUpdateStage
from temporalio.exceptions import ApplicationError

from dan.utils import start_workflow


@workflow.defn
class Workflow:
    @workflow.run
    async def run(self) -> NoReturn:
        await workflow.wait_condition(lambda: False)

    @workflow.update
    async def my_update(self) -> NoReturn:
        raise ApplicationError("deliberate error in update handler")


async def main():
    wf_handle = await start_workflow(Workflow.run)
    update_handle = await wf_handle.start_update(
        Workflow.my_update, wait_for_stage=WorkflowUpdateStage.ACCEPTED
    )
    update_result = await update_handle.result()
    print(f"Update Result: {update_result}")


if __name__ == "__main__":
    asyncio.run(main())
