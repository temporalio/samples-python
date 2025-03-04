import asyncio
import uuid

from temporalio import workflow
from temporalio.client import Client
from temporalio.worker import Worker


@workflow.defn
class SayHello:
    async def _my_task(self) -> None:
        try:
            await workflow.sleep(6, summary="my task")
        except asyncio.CancelledError:
            print("🔴 caught asyncio.CancelledError when sleeping in task")

    @workflow.run
    async def run(self) -> str:
        task = asyncio.create_task(self._my_task())
        await workflow.sleep(2, summary="let the loop start")

        try:
            task.cancel()
            await task
        except BaseException:
            assert False, "unreachable"

        await workflow.sleep(15)
        return "Hello, World!"


async def main():
    client = await Client.connect("localhost:7233")
    task_queue = "timer-callback-exception-task-queue"
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[SayHello],
    ):
        result = await client.execute_workflow(
            SayHello.run,
            id=str(uuid.uuid4()),
            task_queue=task_queue,
        )
        print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
