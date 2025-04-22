import asyncio

from temporalio import workflow
from temporalio.client import Client
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

WORKFLOW_ID = "wid"
TASK_QUEUE = "tq"


@workflow.defn
class Workflow:
    @workflow.run
    async def run(self) -> None:
        await asyncio.Future()


async def main():
    client = await Client.connect("localhost:7233")

    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[Workflow],
        workflow_runner=UnsandboxedWorkflowRunner(),
    ):
        handle = await client.start_workflow(
            Workflow.run, id=WORKFLOW_ID, task_queue=TASK_QUEUE
        )
        await handle.cancel()
        try:
            await handle.result()
        except Exception as e:
            print(
                f"🔴 Exception caught while awaiting workflow after cancellation request: {e.__class__}({e})"
            )
            if e.__cause__ is not None:
                print(f"\t\tcause: {e.__cause__.__class__}({e.__cause__})")


if __name__ == "__main__":
    asyncio.run(main())
