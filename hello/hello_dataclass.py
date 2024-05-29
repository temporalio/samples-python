import asyncio
from dataclasses import dataclass
from datetime import timedelta
import logging

from temporalio import common, workflow, activity
from temporalio.client import Client, WorkflowHandle
from temporalio.worker import Worker


@dataclass
class MyDataclass:
    my_field: int


@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self, arg: MyDataclass) -> MyDataclass:
        if True:
            return await workflow.execute_activity(
                my_activity,
                arg=MyDataclass(1),
                start_to_close_timeout=timedelta(seconds=10),
            )
        return MyDataclass(arg.my_field + 1)


@activity.defn
async def my_activity(arg: MyDataclass) -> MyDataclass:
    return MyDataclass(arg.my_field + 2)


async def app(wf: WorkflowHandle):
    wf_result = await wf.result()
    print(f"wf result: {wf_result}")


async def main():
    client = await Client.connect("localhost:7233")
    async with Worker(
        client,
        task_queue="tq",
        workflows=[MyWorkflow],
        activities=[
            my_activity,
        ],
    ):
        wf = await client.start_workflow(
            MyWorkflow.run,
            arg=MyDataclass(my_field=1),
            id="wid",
            task_queue="tq",
            id_reuse_policy=common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
        )
        await app(wf)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
