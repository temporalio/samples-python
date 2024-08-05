import asyncio

from temporalio import common, workflow
from temporalio.client import Client
from temporalio.worker import Worker

wid = __file__
tq = "tq"


@workflow.defn
class Workflow:
    def __init__(self):
        self.is_complete = False

    @workflow.run
    async def run(self) -> str:
        await workflow.wait_condition(lambda: self.is_complete)
        return "Hello, World!"

    @workflow.update
    async def update_workflow_status(self) -> str:
        self.is_complete = True
        return "Workflow status updated"


async def main():
    client = await Client.connect("localhost:7233")
    async with Worker(
        client,
        task_queue=tq,
        workflows=[Workflow],
    ):
        handle = await client.start_workflow(
            Workflow.run,
            id=wid,
            task_queue=tq,
            id_reuse_policy=common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
        )
        update_result = await handle.execute_update(Workflow.update_workflow_status)
        print(f"Update Result: {update_result}")
        result = await handle.result()
        print(f"Workflow Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
