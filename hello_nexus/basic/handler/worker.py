import asyncio
import logging
from typing import Optional

from temporalio.client import Client
from temporalio.worker import Worker

from hello_nexus.basic.handler.db_client import MyDBClient
from hello_nexus.basic.handler.service_handler import MyNexusServiceHandler
from hello_nexus.basic.handler.service_handler_with_operation_handler_classes import (
    MyNexusServiceHandlerUsingOperationHandlerClasses,
)
from hello_nexus.basic.handler.workflows import WorkflowStartedByNexusOperation

interrupt_event = asyncio.Event()

NAMESPACE = "my-target-namespace"
TASK_QUEUE = "my-target-task-queue"


async def main(
    client: Optional[Client] = None,
    # Change this to use the service handler defined in
    # hello_nexus/basic/handler/service_handler_with_operation_handler_classes.py
    use_operation_handler_classes: bool = False,
):
    logging.basicConfig(level=logging.INFO)

    client = client or await Client.connect(
        "localhost:7233",
        namespace=NAMESPACE,
    )

    # Create an instance of the service handler. Your service handler class __init__ can
    # be written to accept any arguments that your operation handlers need when handling
    # requests. In this example we provide a database client object to the service hander.
    connected_db_client = MyDBClient.connect()

    my_nexus_service_handler = (
        MyNexusServiceHandlerUsingOperationHandlerClasses(
            connected_db_client=connected_db_client
        )
        if use_operation_handler_classes
        else MyNexusServiceHandler(connected_db_client=connected_db_client)
    )

    # Start the worker, passing the Nexus service handler instance, in addition to the
    # workflow classes that are started by your nexus operations, and any activities
    # needed. This Worker will poll for both workflow tasks and Nexus tasks (this example
    # doesn't use any activities).
    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[WorkflowStartedByNexusOperation],
        nexus_services=[my_nexus_service_handler],
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
