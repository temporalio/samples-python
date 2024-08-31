import asyncio

from temporalio import workflow
from temporalio.client import WorkflowUpdateStage

from dan.utils import start_workflow

wid = "wid-unt"


@workflow.defn
class Workflow:
    def __init__(self):
        self.is_complete = False

    @workflow.run
    async def run(self) -> str:
        await workflow.wait_condition(lambda: self.is_complete)
        return "Hello, World!"

    @workflow.update
    async def my_update(self) -> str:
        return "update result"


async def main():
    handle = await start_workflow(Workflow.run, id=wid)
    update_handle = await handle.start_update(
        "my_update_xxx", wait_for_stage=WorkflowUpdateStage.ACCEPTED
    )
    print("Update Handle:")
    from pprint import pprint

    pprint(update_handle.__dict__)

    # update_result = await update_handle.result()
    # print(f"Update Result: {update_result}")
    # result = await handle.result()
    # print(f"Workflow Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
