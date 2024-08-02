import asyncio

from temporalio import workflow
from temporalio.client import Client
from temporalio.worker import Worker

wid = __file__
tq = "tq"


@workflow.defn
class Workflow:
    @workflow.run
    async def run(self):
        await asyncio.gather(coro1(), coro2())


async def temporal_main():
    client = await Client.connect("localhost:7233")
    async with Worker(
        client,
        task_queue=tq,
        workflows=[Workflow],
    ):
        await client.execute_workflow(Workflow.run, id=wid, task_queue=tq)


lock = asyncio.Lock()


async def coro1():
    print("coro1 trying to acquire lock")
    async with lock:
        print("coro1 acquired lock")
        await asyncio.sleep(float("inf"))


async def coro2():
    print("coro2 trying to acquire lock")
    async with lock:
        print("coro2 acquired lock")
        await asyncio.sleep(float("inf"))


async def main():
    await asyncio.gather(coro1(), coro2())


if __name__ == "__main__":
    asyncio.run(temporal_main())
