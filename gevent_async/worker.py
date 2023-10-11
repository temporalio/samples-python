# Init gevent
from gevent import monkey

monkey.patch_all()
import asyncio
import logging
import signal

import gevent
from temporalio.client import Client
from temporalio.worker import Worker

from gevent_async import activity, workflow
from gevent_async.executor import GeventExecutor


def main():
    logging.basicConfig(level=logging.INFO)

    # Create a new event loop so we can run_until_complete on it. We could
    # just use asyncio.run like starter does, but this approach allows us to
    # listen for a signal and stop the worker gracefully.
    loop = asyncio.new_event_loop()

    # Make SIGINT trigger an event that will shutdown the worker
    interrupt_event = asyncio.Event()
    gevent.signal_handler(signal.SIGINT, loop.call_soon_threadsafe, interrupt_event.set)

    # Create single-worker gevent executor to run event loop, waiting for
    # result. This executor cannot be used for anything else in Temporal, it is
    # just a single thread for running asyncio. This means that inside of
    # async_main we must create another executor specifically for executing
    # activity and workflow tasks.
    with GeventExecutor(max_workers=1) as executor:
        executor.submit(loop.run_until_complete, async_main(interrupt_event)).result()


async def async_main(interrupt_event: asyncio.Event):
    # Connect client
    client = await Client.connect("localhost:7233")

    # Create an executor for use by Temporal. This cannot be the outer one
    # running this async main. The max_workers here needs to have enough room to
    # support the max concurrent activities/workflows settings.
    with GeventExecutor(max_workers=200) as executor:

        # Run a worker for the workflow and activities
        async with Worker(
            client,
            task_queue="gevent_async-task-queue",
            workflows=[workflow.GreetingWorkflow],
            activities=[
                activity.compose_greeting_async,
                activity.compose_greeting_sync,
            ],
            # Set the executor for activities (only used for non-async
            # activities) and workflow tasks
            activity_executor=executor,
            workflow_task_executor=executor,
            # Set the max concurrent activities/workflows. These are the same as
            # the defaults, but this makes it clear that the 100 + 100 = 200 for
            # max_workers settings.
            max_concurrent_activities=100,
            max_concurrent_workflow_tasks=100,
        ):

            # Wait until interrupted
            logging.info("Worker started, ctrl+c to exit")
            await interrupt_event.wait()
            logging.info("Shutting down")


if __name__ == "__main__":
    main()
