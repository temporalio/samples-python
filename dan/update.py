import asyncio

from temporalio import workflow

from dan.utils import start_workflow

wid = __file__


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
        self.is_complete = True
        return "Workflow status updated"


async def main():
    handle = await start_workflow(Workflow.run, id=wid)
    update_result = await handle.execute_update(Workflow.my_update)
    print(f"Update Result: {update_result}")
    result = await handle.result()
    print(f"Workflow Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
