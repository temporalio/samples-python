import asyncio
import logging
from typing import Optional

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from hello_nexus.handler.service_handler import MyNexusServiceHandler
from hello_nexus.handler.workflows import WorkflowStartedByNexusOperation
from util import get_temporal_config_path

interrupt_event = asyncio.Event()

NAMESPACE = "hello-nexus-basic-handler-namespace"
TASK_QUEUE = "my-handler-task-queue"


async def main(client: Optional[Client] = None):
    logging.basicConfig(level=logging.INFO)

    if not client:
        config = ClientConfig.load_client_connect_config(
            config_file=str(get_temporal_config_path())
        )
        # Override the namespace from the config file.
        config["namespace"] = NAMESPACE
        client = await Client.connect(**config)

    # Start the worker, passing the Nexus service handler instance, in addition to the
    # workflow classes that are started by your nexus operations, and any activities
    # needed. This Worker will poll for both workflow tasks and Nexus tasks (this example
    # doesn't use any activities).
    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[WorkflowStartedByNexusOperation],
        nexus_service_handlers=[MyNexusServiceHandler()],
    ):
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
