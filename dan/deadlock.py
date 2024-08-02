import asyncio

from temporalio import common, workflow
from temporalio.client import Client
from temporalio.worker import Worker

wid = __file__
tq = "tq"


@workflow.defn
class Workflow:
    def __init__(self) -> None:
        self.resource_1_available = False
        self.resource_2_available = False

    @workflow.run
    async def run(self):
        await asyncio.gather(self.coro1(), self.coro2())

    async def coro1(self):
        await workflow.wait_condition(lambda: self.resource_2_available)
        self.resource_1_available = True

    async def coro2(self):
        await workflow.wait_condition(lambda: self.resource_1_available)
        self.resource_2_available = True

    @workflow.signal
    def release_resource_1(self):
        self.resource_1_available = True


resource1 = asyncio.Lock()
resource2 = asyncio.Lock()


async def coro1():
    print("coro1 trying to acquire resource1")
    await resource1.acquire()
    print("coro1 acquired resource1")
    await asyncio.sleep(0)
    async with resource2:
        print("coro1 acquired resource2")
    if resource1.locked():
        resource1.release()


async def coro2():
    print("coro2 trying to acquire resource2")
    async with resource2:
        print("coro2 acquired resource2")
        await asyncio.sleep(0)
        await resource1.acquire()
        print("coro2 acquired resource1")
        if resource1.locked():
            resource1.release()


async def coro3():
    await asyncio.sleep(1)
    print("coro3 releasing resource1")
    resource1.release()


async def temporal_main():
    client = await Client.connect("localhost:7233")
    async with Worker(
        client,
        task_queue=tq,
        workflows=[Workflow],
    ):
        await client.execute_workflow(
            Workflow.run,
            id=wid,
            task_queue=tq,
            id_reuse_policy=common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
        )


async def main():
    await asyncio.gather(coro1(), coro2(), coro3())


if __name__ == "__main__":
    asyncio.run(temporal_main())
