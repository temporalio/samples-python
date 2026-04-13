import asyncio
import logging
from typing import Optional

from temporalio.client import Client
from temporalio.common import WorkflowIDConflictPolicy
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from nexus_messaging.callerpattern.handler.activities import call_greeting_service
from nexus_messaging.callerpattern.handler.service_handler import (
    NexusGreetingServiceHandler,
    get_workflow_id,
)
from nexus_messaging.callerpattern.handler.workflows import GreetingWorkflow

interrupt_event = asyncio.Event()

NAMESPACE = "nexus-messaging-handler-namespace"
TASK_QUEUE = "nexus-messaging-handler-task-queue"
USER_ID = "user-1"


async def main(client: Optional[Client] = None):
    logging.basicConfig(level=logging.INFO)

    if client is None:
        config = ClientConfig.load_client_connect_config()
        config.setdefault("target_host", "localhost:7233")
        config.setdefault("namespace", NAMESPACE)
        client = await Client.connect(**config)

    # Start the long-running entity workflow that backs the Nexus service,
    # if not already running.
    workflow_id = get_workflow_id(USER_ID)
    await client.start_workflow(
        GreetingWorkflow.run,
        id=workflow_id,
        task_queue=TASK_QUEUE,
        id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
    )
    logging.info("Started greeting workflow: %s", workflow_id)

    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[GreetingWorkflow],
        activities=[call_greeting_service],
        nexus_service_handlers=[NexusGreetingServiceHandler()],
    ):
        logging.info("Handler worker started, ctrl+c to exit")
        await interrupt_event.wait()
        logging.info("Shutting down")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
