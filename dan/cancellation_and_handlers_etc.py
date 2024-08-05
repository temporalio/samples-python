import asyncio
from datetime import timedelta

import rich
import temporalio
import temporalio.client
import temporalio.exceptions
from temporalio import activity, common, workflow
from temporalio.client import Client, WorkflowUpdateStage
from temporalio.common import RetryPolicy
from temporalio.worker import Worker

wid = __file__
tq = "tq"


@activity.defn
async def my_activity():
    print("in activity")
    raise Exception("activity error")


@workflow.defn
class Workflow:
    """
    A workflow that is canceled while handlers are running.
    """

    def __init__(self) -> None:
        self.handler_in_progress = False

    @workflow.run
    async def run(self) -> str:
        await workflow.wait_condition(lambda: self.handler_in_progress)
        try:
            await workflow.execute_activity(
                my_activity,
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=RetryPolicy(maximum_attempts=1),
            )
        except temporalio.exceptions.ActivityError as err:
            print(f"[red]Workflow: ActivityError: {err.__class__.__name__}[/red]")
        return "wf-result"

    @workflow.update
    async def my_update(self) -> str:
        self.handler_in_progress = True
        # await workflow.wait_condition(lambda: False)
        return "update-result"


async def main():
    client = await Client.connect("localhost:7233")
    async with Worker(
        client,
        task_queue=tq,
        workflows=[Workflow],
        activities=[my_activity],
    ):
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

        # await wf_handle.cancel()

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
