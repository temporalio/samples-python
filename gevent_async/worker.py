# Init gevent
from gevent import monkey

monkey.patch_all()

import asyncio
import logging
import signal

import gevent
from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from gevent_async import activity, workflow
from gevent_async.executor import GeventExecutor


def main():
    logging.basicConfig(level=logging.INFO)

    # Create single-worker gevent executor and run asyncio.run(async_main()) in
    # it, waiting for result. This executor cannot be used for anything else in
    # Temporal, it is just a single thread for running asyncio. This means that
    # inside of async_main we must create another executor specifically for
    # executing activity and workflow tasks.
    with GeventExecutor(max_workers=1) as executor:
        executor.submit(asyncio.run, async_main()).result()


async def async_main():
    # Create ctrl+c handler. We do this by telling gevent on SIGINT to set the
    # asyncio event. But asyncio calls are not thread safe, so we have to invoke
    # it via call_soon_threadsafe.
    interrupt_event = asyncio.Event()
    gevent.signal_handler(
        signal.SIGINT,
        asyncio.get_running_loop().call_soon_threadsafe,
        interrupt_event.set,
    )

    # Connect client
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

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
