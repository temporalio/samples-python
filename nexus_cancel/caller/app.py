import asyncio
import uuid
from typing import Optional

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from nexus_cancel.caller.workflows import HelloCallerWorkflow

NAMESPACE = "nexus-cancel-caller-namespace"
TASK_QUEUE = "nexus-cancel-caller-task-queue"


async def execute_caller_workflow(
    client: Optional[Client] = None,
) -> str:
    if client is None:
        config = ClientConfig.load_client_connect_config()
        config.setdefault("target_host", "localhost:7233")
        config.setdefault("namespace", NAMESPACE)
        client = await Client.connect(**config)

    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[HelloCallerWorkflow],
    ):
        return await client.execute_workflow(
            HelloCallerWorkflow.run,
            "Nexus",
            id=f"hello-caller-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(execute_caller_workflow())
        print(result)
    except KeyboardInterrupt:
        loop.run_until_complete(loop.shutdown_asyncgens())
