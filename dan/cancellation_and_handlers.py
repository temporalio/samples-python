import asyncio
from typing import NoReturn

import temporalio
import temporalio.client
import temporalio.exceptions
from rich import print
from temporalio import common, workflow
from temporalio.client import Client
from temporalio.worker import Worker

wid = __file__
tq = "tq"


@workflow.defn
class Workflow:
    """
    A workflow that is canceled while handlers are running.
    """

    @workflow.run
    async def run(self) -> NoReturn:
        await workflow.wait_condition(lambda: False)

    @workflow.update
    async def my_update(self) -> NoReturn:
        await workflow.wait_condition(lambda: False)


async def main():
    client = await Client.connect("localhost:7233")
    async with Worker(
        client,
        task_queue=tq,
        workflows=[Workflow],
    ):
        wf_handle = await client.start_workflow(
            Workflow.run,
            id=wid,
            task_queue=tq,
            id_reuse_policy=common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
        )

        # Start an Update, wait until the handler is executing, then cancel the workflow.
        upd_handle = await wf_handle.start_update(Workflow.my_update)

        await wf_handle.cancel()

        try:
            print(await upd_handle.result())
        except temporalio.service.RPCError as err:
            print(f"[red]Client: error while waiting for update result: {err}[/red]")

        try:
            print(await wf_handle.result())
        except temporalio.client.WorkflowFailureError as err:
            print(f"[red]Client: error while waiting for workflow result: {err}[/red]")


if __name__ == "__main__":
    asyncio.run(main())
