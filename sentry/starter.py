import asyncio
import os
from pathlib import Path

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from sentry.worker import GreetingWorkflow


async def main():
    # Get repo root - 1 level deep from root

    repo_root = Path(__file__).resolve().parent.parent

    config_file = repo_root / "temporal.toml"

    
    config = ClientConfig.load_client_connect_config(config_file=str(config_file))
    config["target_host"] = "localhost:7233"
    
    # Connect client
    client = await Client.connect(**config)

    # Run workflow
    result = await client.execute_workflow(
        GreetingWorkflow.run,
        "World",
        id="sentry-workflow-id",
        task_queue="sentry-task-queue",
    )
    print(f"Workflow result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
