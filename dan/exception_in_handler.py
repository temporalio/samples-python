import asyncio

import temporalio
import temporalio.client
import temporalio.exceptions
import temporalio.workflow
from rich import print
from temporalio import common, workflow
from temporalio.client import Client
from temporalio.worker import Worker

wid = __file__
tq = "tq"


@workflow.defn
class HelloWorldWorkflow:
    def __init__(self):
        self.workflow_has_started = False
        self.update_has_started = False

    @workflow.run
    async def run(self) -> str:
        self.workflow_has_started = True
        await workflow.wait_condition(lambda: self.update_has_started)
        return "workflow-result"

    @workflow.update
    async def my_update(self) -> str:
        await workflow.wait_condition(lambda: self.workflow_has_started)
        self.update_has_started = True
        if False:
            raise temporalio.exceptions.ApplicationError(
                "Workflow author raised Exception in update handler"
            )
        else:
            raise Exception("Unexpected Exception in update handler")


async def main():
    client = await Client.connect("localhost:7233")
    async with Worker(
        client,
        task_queue=tq,
        workflows=[HelloWorldWorkflow],
    ):
        handle = await client.start_workflow(
            HelloWorldWorkflow.run,
            id=wid,
            task_queue=tq,
            id_reuse_policy=common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
        )
        try:
            with open("/tmp/client", "a") as f:
                print("[orange]executing update...[/orange]", file=f)
            await handle.execute_update(HelloWorldWorkflow.my_update)
        except temporalio.client.WorkflowUpdateFailedError as err:
            with open("/tmp/client", "a") as f:
                print(f"[red]Got error: {err}[/red]", file=f)

        # Failed update does not fail workflows
        with open("/tmp/client", "a") as f:
            print(f"[green]wf-result: {await handle.result()}[/green]", file=f)


if __name__ == "__main__":
    asyncio.run(main())
