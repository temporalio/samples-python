import asyncio
import uuid
from typing import Optional

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from nexus_multiple_args.caller.workflows import CallerWorkflow

NAMESPACE = "nexus-multiple-args-caller-namespace"
TASK_QUEUE = "nexus-multiple-args-caller-task-queue"


async def execute_caller_workflow(
    client: Optional[Client] = None,
) -> tuple[str, str]:
    if client is None:
        config = ClientConfig.load_client_connect_config()
        config.setdefault("target_host", "localhost:7233")
        client = await Client.connect(**config, namespace=NAMESPACE)

    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[CallerWorkflow],
    ):
        # Execute workflow with English language
        result1 = await client.execute_workflow(
            CallerWorkflow.run,
            args=["Nexus", "en"],
            id=str(uuid.uuid4()),
            task_queue=TASK_QUEUE,
        )

        # Execute workflow with Spanish language
        result2 = await client.execute_workflow(
            CallerWorkflow.run,
            args=["Nexus", "es"],
            id=str(uuid.uuid4()),
            task_queue=TASK_QUEUE,
        )

        return result1, result2


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        results = loop.run_until_complete(execute_caller_workflow())
        for result in results:
            print(result)
    except KeyboardInterrupt:
        loop.run_until_complete(loop.shutdown_asyncgens())
