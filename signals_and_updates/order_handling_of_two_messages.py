import asyncio
import logging

from temporalio import common, workflow
from temporalio.client import Client, WorkflowHandle
from temporalio.worker import Worker


@workflow.defn
class WashAndDryCycle:

    def __init__(self) -> None:
        self.wash_complete = False
        self.dry_complete = False

    @workflow.run
    async def run(self):
        await workflow.wait_condition(lambda: self.dry_complete)

    @workflow.update
    async def wash(self):
        self.wash_complete = True
        workflow.logger.info("washing")

    @workflow.update
    async def dry(self):
        await workflow.wait_condition(lambda: self.wash_complete)
        self.dry_complete = True
        workflow.logger.info("drying")


async def app(wf: WorkflowHandle):
    await asyncio.gather(
        wf.execute_update(WashAndDryCycle.dry), wf.execute_update(WashAndDryCycle.wash)
    )


async def main():
    client = await Client.connect("localhost:7233")

    async with Worker(
        client,
        task_queue="tq",
        workflows=[WashAndDryCycle],
    ):
        handle = await client.start_workflow(
            WashAndDryCycle.run,
            id="wid",
            task_queue="tq",
            id_reuse_policy=common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
        )
        await app(handle)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
