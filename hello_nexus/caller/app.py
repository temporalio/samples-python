import asyncio
import uuid
from typing import Optional

from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile
from temporalio.worker import Worker

from hello_nexus.caller.workflows import CallerWorkflow
from hello_nexus.service import MyOutput

NAMESPACE = "hello-nexus-basic-caller-namespace"
TASK_QUEUE = "hello-nexus-basic-caller-task-queue"


async def execute_caller_workflow(
    client: Optional[Client] = None,
) -> tuple[MyOutput, MyOutput]:
    if not client:
        config_dict = ClientConfigProfile.load().to_dict()
        # Override the namespace from config file.
        config_dict.setdefault("address", "localhost:7233")
        config_dict["namespace"] = NAMESPACE
        config = ClientConfigProfile.from_dict(config_dict)
        client = await Client.connect(**config.to_client_connect_config())

    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[CallerWorkflow],
    ):
        return await client.execute_workflow(
            CallerWorkflow.run,
            arg="world",
            id=str(uuid.uuid4()),
            task_queue=TASK_QUEUE,
        )


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        results = loop.run_until_complete(execute_caller_workflow())
        for output in results:
            print(output.message)
    except KeyboardInterrupt:
        loop.run_until_complete(loop.shutdown_asyncgens())
