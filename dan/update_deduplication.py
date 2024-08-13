import asyncio
import itertools
from typing import Optional

from temporalio import workflow
from temporalio.exceptions import ApplicationError
from utils import start_workflow


@workflow.defn
class Workflow:
    def __init__(self) -> None:
        self.update_ids = set[str]()

    @workflow.run
    async def run(self, update_ids: Optional[set[str]] = None) -> str:
        self.update_ids = update_ids or set[str]()
        while 1:
            await workflow.wait_condition(
                lambda: workflow.info().is_continue_as_new_suggested()
            )
            print("CAN")
            workflow.continue_as_new(self.update_ids)
        return "workflow-result"

    @workflow.update
    def my_update(self) -> str:
        assert (update := workflow.current_update_info())
        if update.id in self.update_ids:
            raise ApplicationError(f"duplicate update ID: {update.id}")
        self.update_ids.add(update.id)
        return update.id


async def main():
    wf_handle = await start_workflow(Workflow.run)

    for i in itertools.count():
        print(await wf_handle.execute_update(Workflow.my_update, id=str(i)))
    #        print(await wf_handle.execute_update(Workflow.my_update, id=str(i)))

    print("workflow result:", await wf_handle.result())


if __name__ == "__main__":
    asyncio.run(main())
