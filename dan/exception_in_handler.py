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
        raise temporalio.exceptions.ApplicationError(
            "Workflow author raised Exception in update handler"
        )


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
            await handle.execute_update(HelloWorldWorkflow.my_update)
        except temporalio.client.WorkflowUpdateFailedError as err:
            print(f"[red]Got error: {err}[/red]")

        # Failed update does not fail workflows
        print(f"[green]wf-result: {await handle.result()}[/green]")


if __name__ == "__main__":
    asyncio.run(main())
