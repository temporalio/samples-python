import asyncio
import logging
from datetime import timedelta

from temporalio import activity, common, workflow
from temporalio.client import Client, WorkflowHandle
from temporalio.worker import Worker


@workflow.defn
class WashAndDryCycle:

    def __init__(self) -> None:
        self.has_detergent = False
        self.wash_complete = False
        self.non_dryables_removed = False
        self.dry_complete = False

    @workflow.run
    async def run(self):
        await workflow.execute_activity(
            add_detergent, start_to_close_timeout=timedelta(seconds=10)
        )
        self.has_detergent = True
        await workflow.wait_condition(lambda: self.wash_complete)
        await workflow.execute_activity(
            remove_non_dryables, start_to_close_timeout=timedelta(seconds=10)
        )
        self.non_dryables_removed = True
        await workflow.wait_condition(lambda: self.dry_complete)

    @workflow.update
    async def wash(self):
        await workflow.wait_condition(lambda: self.has_detergent)
        self.wash_complete = True
        workflow.logger.info("washing")

    @workflow.update
    async def dry(self):
        await workflow.wait_condition(
            lambda: self.wash_complete and self.non_dryables_removed
        )
        self.dry_complete = True
        workflow.logger.info("drying")


@activity.defn
async def add_detergent():
    print("adding detergent")


@activity.defn
async def remove_non_dryables():
    print("removing non-dryables")


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
        activities=[add_detergent, remove_non_dryables],
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
