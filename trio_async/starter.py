import logging

import trio_asyncio
from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile

from trio_async import workflows


@trio_asyncio.aio_as_trio  # Note this decorator which allows asyncio primitives
async def main():
    logging.basicConfig(level=logging.INFO)

    # Connect client
    config_dict = ClientConfigProfile.load().to_dict()
    config_dict.setdefault("address", "localhost:7233")
    config = ClientConfigProfile.from_dict(config_dict)
    client = await Client.connect(**config.to_client_connect_config())

    # Execute the workflow
    result = await client.execute_workflow(
        workflows.SayHelloWorkflow.run,
        "Temporal",
        id=f"trio-async-workflow-id",
        task_queue="trio-async-task-queue",
    )
    logging.info(f"Workflow result: {result}")


if __name__ == "__main__":
    # Note how we're using Trio event loop, not asyncio
    trio_asyncio.run(main)
