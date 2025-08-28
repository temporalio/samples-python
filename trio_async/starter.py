import logging

import trio_asyncio
from temporalio.client import Client

from trio_async import workflows


@trio_asyncio.aio_as_trio  # Note this decorator which allows asyncio primitives
async def main():
    logging.basicConfig(level=logging.INFO)

    # Connect client
        # Get repo root - 1 level deep from root
        repo_root = Path(__file__).resolve().parent.parent
        config_file = repo_root / "temporal.toml"
    config = ClientConfig.load_client_connect_config(config_file=str(config_file))
    config["target_host"] = "localhost:7233"
    client = await Client.connect(**config)

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
