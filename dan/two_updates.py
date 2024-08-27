import asyncio

from temporalio import workflow

from dan.utils import start_workflow

wid = "wid"


@workflow.defn
class Workflow:
    def __init__(self):
        self.update1_may_continue = False
        self.is_complete = False

    @workflow.run
    async def run(self) -> str:
        print("workflow: starting and waiting")
        await workflow.wait_condition(lambda: self.is_complete)
        print("workflow waiting for ever")
        await workflow.wait_condition(lambda: False)
        return "Hello, World!"

    @workflow.update
    async def update1(self) -> str:
        print("update1: starting and waiting")
        await workflow.wait_condition(lambda: self.update1_may_continue)
        self.is_complete = True
        return "update1: complete"

    @workflow.update
    async def update2(self) -> str:
        print("update2: starting")
        self.update1_may_continue = True
        return "update2: complete"


async def main():
    handle = await start_workflow(Workflow.run, id=wid)
    result = await handle.result()
    # temporal workflow update --workflow-id wid --name update1 --namespace ns
    # temporal workflow update execute --workflow-id wid --name update1 --task-queue tq --namespace ns
    print(f"Workflow Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
