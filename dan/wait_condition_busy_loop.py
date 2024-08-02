import asyncio
from typing import NoReturn

from temporalio import workflow
from temporalio.client import Client
from temporalio.worker import Worker

wid = __file__
tq = "tq"


@workflow.defn
class Workflow:
    @workflow.run
    async def run(self) -> NoReturn:
        while True:
            await workflow.wait_condition(lambda: True)


async def main():
    client = await Client.connect("localhost:7233")
    async with Worker(
        client,
        task_queue=tq,
        workflows=[Workflow],
    ):
        handle = await client.start_workflow(Workflow.run, id=wid, task_queue=tq)
        await handle.result()


if __name__ == "__main__":
    asyncio.run(main())
