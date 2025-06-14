import asyncio
import logging
import os
import sys

import trio_asyncio
from temporalio.client import Client
from temporalio.worker import Worker

from trio_async import activities, workflows


@trio_asyncio.aio_as_trio  # Note this decorator which allows asyncio primitives
async def main():
    logging.basicConfig(level=logging.INFO)

    # Connect client
    client = await Client.connect("localhost:7233")

    # Temporal runs threaded activities and workflow tasks via run_in_executor.
    # Due to how trio_asyncio works, you can only do run_in_executor with their
    # specific executor. We make sure to give it 200 max since we are using it
    # for both activities and workflow tasks and by default the worker supports
    # 100 max concurrent activity tasks and 100 max concurrent workflow tasks.
    with trio_asyncio.TrioExecutor(max_workers=200) as thread_executor:

        # Run a worker for the workflow
        async with Worker(
            client,
            task_queue="trio-async-task-queue",
            activities=[
                activities.say_hello_activity_async,
                activities.say_hello_activity_sync,
            ],
            workflows=[workflows.SayHelloWorkflow],
            activity_executor=thread_executor,
            workflow_task_executor=thread_executor,
        ):
            # Wait until interrupted
            logging.info("Worker started, ctrl+c to exit")
            try:
                await asyncio.Future()
            except asyncio.CancelledError:
                # Ignore, happens on ctrl+C
                pass
            finally:
                logging.info("Shutting down")


if __name__ == "__main__":
    # Note how we're using Trio event loop, not asyncio
    try:
        trio_asyncio.run(main)
    except KeyboardInterrupt:
        # Ignore ctrl+c
        pass
    except BaseException as err:
        # On Python 3.11+ Trio represents keyboard interrupt inside an exception
        # group
        is_interrupt = (
            sys.version_info >= (3, 11)
            and isinstance(err, BaseExceptionGroup)
            and err.subgroup(KeyboardInterrupt)
        )
        if not is_interrupt:
            raise
