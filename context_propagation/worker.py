import asyncio
import logging

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from context_propagation import activities, interceptor, workflows
from util import get_temporal_config_path

interrupt_event = asyncio.Event()


async def main():
    logging.basicConfig(level=logging.INFO)

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")

    # Connect client
    client = await Client.connect(
        **config,
        # Use our interceptor
        interceptors=[interceptor.ContextPropagationInterceptor()],
    )

    # Run a worker for the workflow
    async with Worker(
        client,
        task_queue="context-propagation-task-queue",
        activities=[activities.say_hello_activity],
        workflows=[workflows.SayHelloWorkflow],
    ):
        # Wait until interrupted
        logging.info("Worker started, ctrl+c to exit")
        await interrupt_event.wait()
        logging.info("Shutting down")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
