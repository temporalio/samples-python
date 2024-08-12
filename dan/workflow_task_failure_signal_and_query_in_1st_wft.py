import asyncio

from temporalio import workflow
from utils import ainput, catch, start_workflow


@workflow.defn
class Workflow:
    @workflow.run
    async def run(self) -> str:
        await workflow.wait_condition(lambda: False)
        return "workflow-result"

    @workflow.query
    def my_query(self) -> str:
        a, b = 1, 1
        while True:
            a, b = b, a + b
        return "query-result"

    @workflow.signal
    async def my_signal(self):
        pass


async def main():
    """
    We make the first WFT contain a signal and a query, then raise an exception in the query handler.
    """
    await ainput("The worker's not running, right?")
    wf_handle = await start_workflow(Workflow.run)
    await wf_handle.signal(Workflow.my_signal)
    task = asyncio.create_task(wf_handle.query(Workflow.my_query))

    await ainput("Start the worker now")
    with catch():
        print("query result:", await task)


if __name__ == "__main__":
    asyncio.run(main())
