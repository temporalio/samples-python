import asyncio
import itertools
from typing import Optional

from temporalio import workflow
from temporalio.exceptions import ApplicationError
from utils import start_workflow

NUM_DUPS = 20


@workflow.defn
class Workflow:
    def __init__(self) -> None:
        self.update_ids = None

    @workflow.run
    async def run(self, update_ids: Optional[set[str]] = None) -> str:
        self.update_ids = update_ids or set[str]()
        while 1:
            await workflow.wait_condition(
                lambda: workflow.info().is_continue_as_new_suggested()
            )
            print("🔵🔵🔵🔵🔵🔵🔵 CAN")
            workflow.continue_as_new(self.update_ids)
        return "workflow-result"

    @workflow.update
    async def my_update(self) -> list[str]:
        await workflow.wait_condition(lambda: self.update_ids is not None)
        assert self.update_ids is not None
        assert (update := workflow.current_update_info())
        if update.id in self.update_ids:
            raise ApplicationError(f"duplicate update ID: {update.id}")
        self.update_ids.add(update.id)
        # return sorted(self.update_ids, key=int)
        return ["b"]


async def main():
    wf_handle = await start_workflow(Workflow.run)

    for i in itertools.count():
        for _ in range(NUM_DUPS):
            print(await wf_handle.execute_update(Workflow.my_update, id=str(i)))

    print("workflow result:", await wf_handle.result())


if __name__ == "__main__":
    asyncio.run(main())
