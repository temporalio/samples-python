import asyncio
import uuid
from pathlib import Path
from typing import Optional

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from hello_nexus.caller.workflows import CallerWorkflow
from hello_nexus.service import MyOutput

NAMESPACE = "hello-nexus-basic-caller-namespace"
TASK_QUEUE = "hello-nexus-basic-caller-task-queue"


async def execute_caller_workflow(
    client: Optional[Client] = None,
) -> tuple[MyOutput, MyOutput]:
    if not client:
        # Get repo root - 2 levels deep from root

        repo_root = Path(__file__).resolve().parent.parent.parent

        config_file = repo_root / "temporal.toml"

        
        config = ClientConfig.load_client_connect_config(config_file=str(config_file))
        config["target_host"] = "localhost:7233"
        config["namespace"] = NAMESPACE
        client = await Client.connect(**config)

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
