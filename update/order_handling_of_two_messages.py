import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from temporalio import common, workflow
from temporalio.client import Client, WorkflowHandle
from temporalio.worker import Worker


# Shows how to make a pair of update or signal handlers run in a certain order even
# if they are received out of order.
@workflow.defn
class WashAndDryCycle:

    @dataclass
    class WashResults:
        num_items: int

    @dataclass
    class DryResults:
        num_items: int
        moisture_level: int

    def __init__(self) -> None:
        self._wash_results: Optional[WashAndDryCycle.WashResults] = None
        self._dry_results: Optional[WashAndDryCycle.DryResults] = None

    @workflow.run
    async def run(self):
        await workflow.wait_condition(lambda: self._dry_results is not None)
        assert self._dry_results
        workflow.logger.info(
            f"Finished washing and drying {self._dry_results.num_items} items, moisture level: {self._dry_results.moisture_level}"
        )

    @workflow.update
    async def wash(self, num_items) -> WashResults:
        self._wash_results = WashAndDryCycle.WashResults(num_items=num_items)
        return self._wash_results

    @workflow.update
    async def dry(self) -> DryResults:
        await workflow.wait_condition(lambda: self._wash_results is not None)
        assert self._wash_results
        self._dry_results = WashAndDryCycle.DryResults(
            num_items=self._wash_results.num_items, moisture_level=3
        )
        return self._dry_results


async def app(wf: WorkflowHandle):
    # In normal operation, wash comes before dry, but here we simulate out-of-order receipt of messages
    await asyncio.gather(
        wf.execute_update(WashAndDryCycle.dry),
        wf.execute_update(WashAndDryCycle.wash, 10),
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
