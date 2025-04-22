import asyncio

from hyperlinked import print
from temporalio import workflow
from temporalio.client import Client
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

WORKFLOW_ID = "wid"
TASK_QUEUE = "tq"


@workflow.defn
class Workflow:
    @workflow.run
    async def run(self) -> None:
        return


async def main():
    client = await Client.connect("localhost:7233")

    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[Workflow],
        workflow_runner=UnsandboxedWorkflowRunner(),
    ):
        result = await client.execute_workflow(
            Workflow.run, id=WORKFLOW_ID, task_queue=TASK_QUEUE
        )
        print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
