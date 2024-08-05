import asyncio
from typing import NoReturn

import rich
import temporalio
import temporalio.client
import temporalio.exceptions
from temporalio import common, workflow
from temporalio.client import Client, WorkflowUpdateStage
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
        try:
            await workflow.wait_condition(lambda: False)
        except asyncio.CancelledError as err:
            print(
                f"[red]Workflow: asyncio.CancelledError while waiting forever: __{err.__class__.__name__}__[/red]"
            )
            # Will wait forever, since update handler currently sees no cancellation
            await workflow.wait_condition(workflow.all_handlers_finished)

    @workflow.update
    async def my_update(self) -> NoReturn:
        await workflow.wait_condition(lambda: False)

    @workflow.signal
    async def my_signal(self) -> NoReturn:
        await workflow.wait_condition(lambda: False)


async def main():
    client = await Client.connect("localhost:7233")
    async with Worker(client, task_queue=tq, workflows=[Workflow]):
        wf_handle = await client.start_workflow(
            Workflow.run,
            id=wid,
            task_queue=tq,
            id_reuse_policy=common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
        )

        # Start an Update, wait until the handler is executing, then cancel the workflow.
        upd_handle = await wf_handle.start_update(
            Workflow.my_update, wait_for_stage=WorkflowUpdateStage.ACCEPTED
        )

        await wf_handle.signal(Workflow.my_signal)

        await wf_handle.cancel()

        try:
            print(await upd_handle.result())
        except temporalio.service.RPCError as err:
            rich.print(
                f"[red]Client: error while waiting for update result: {err}[/red]"
            )

        try:
            print(await wf_handle.result())
        except temporalio.client.WorkflowFailureError as err:
            rich.print(
                f"[red]Client: error while waiting for workflow result: {err}[/red]"
            )


if __name__ == "__main__":
    asyncio.run(main())
