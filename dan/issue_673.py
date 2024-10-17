import asyncio
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Replayer, Worker


@activity.defn
async def test_activity() -> None:
    return


@workflow.defn
class TestWorkflow:
    def __init__(self) -> None:
        self.running_count = 0
        self.state = "stopped"

    @workflow.run
    async def run(self) -> None:
        await asyncio.sleep(1)

    @workflow.signal
    async def start(self) -> None:
        await self.run_one()

    @workflow.update
    async def resume(self) -> None:
        if self.state == "running":
            return
        await self.run_one()

    async def run_one(self):
        self.running_count += 1
        self.state = "running"
        await workflow.execute_activity(
            test_activity,
            start_to_close_timeout=timedelta(seconds=1),
        )
        self.running_count -= 1
        if self.running_count == 0:
            self.state = "stopped"


async def main() -> None:
    id = "wid"
    client = await Client.connect("localhost:7233")
    async with Worker(
        client=client,
        task_queue="test",
        workflows=[TestWorkflow],
        activities=[test_activity],
    ):
        workflow_handle = await client.start_workflow(
            TestWorkflow.run,
            id=id,
            task_queue="test",
        )
        await workflow_handle.signal(TestWorkflow.start)
        await asyncio.sleep(0.5)
        await workflow_handle.execute_update(TestWorkflow.resume)
        await workflow_handle.result()

    workflows = client.list_workflows(f"WorkflowId = '{id}'")
    histories = workflows.map_histories()
    replayer = Replayer(workflows=[TestWorkflow])
    await replayer.replay_workflows(histories)


if __name__ == "__main__":
    asyncio.run(main())
