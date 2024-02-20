import asyncio

from activities import translate_phrase
from temporalio.client import Client
from temporalio.worker import Worker
from workflow import LangChainWorkflow

interrupt_event = asyncio.Event()


async def main():
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client,
        task_queue="langchain-task-queue",
        workflows=[LangChainWorkflow],
        activities=[translate_phrase],
    )

    print("\nWorker started, ctrl+c to exit\n")
    await worker.run()
    try:
        # Wait indefinitely until the interrupt event is set
        await interrupt_event.wait()
    finally:
        # The worker will be shutdown gracefully due to the async context manager
        print("\nShutting down the worker\n")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\nInterrupt received, shutting down...\n")
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
