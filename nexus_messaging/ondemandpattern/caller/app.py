import asyncio
import uuid
from typing import Optional

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from nexus_messaging.ondemandpattern.caller.workflows import CallerRemoteWorkflow

NAMESPACE = "nexus-messaging-caller-namespace"
TASK_QUEUE = "nexus-messaging-caller-remote-task-queue"


async def execute_caller_workflow(client: Optional[Client] = None) -> None:
    if client is None:
        config = ClientConfig.load_client_connect_config()
        config.setdefault("target_host", "localhost:7233")
        config.setdefault("namespace", NAMESPACE)
        client = await Client.connect(**config)

    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[CallerRemoteWorkflow],
    ):
        log = await client.execute_workflow(
            CallerRemoteWorkflow.run,
            id=f"nexus-messaging-remote-caller-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )
        for line in log:
            print(line)


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(execute_caller_workflow())
    except KeyboardInterrupt:
        loop.run_until_complete(loop.shutdown_asyncgens())
