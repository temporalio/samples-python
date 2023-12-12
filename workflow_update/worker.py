import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from workflow_update import HelloWorldWorkflow

interrupt_event = asyncio.Event()


async def main():
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client, task_queue="workflow-update-task-queue", workflows=[HelloWorldWorkflow]
    )
    await worker.run()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
