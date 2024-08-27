import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from dan.constants import NAMESPACE, TASK_QUEUE

# Don't commit the line importing the Workflow class
from dan.two_updates import Workflow

interrupt_event = asyncio.Event()


async def main():
    print(Workflow.__module__)

    client = await Client.connect("localhost:7233", namespace=NAMESPACE)

    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[Workflow],
    ):
        await interrupt_event.wait()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
