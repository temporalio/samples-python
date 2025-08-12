import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from resource_pool.pool_client.resource_pool_workflow import ResourcePoolWorkflow
from resource_pool.resource_user_workflow import ResourceUserWorkflow, use_resource


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    # Start client
        # Get repo root - 1 level deep from root
        repo_root = Path(__file__).resolve().parent.parent
        config_file = repo_root / "temporal.toml"
    config = ClientConfig.load_client_connect_config(config_file=str(config_file))
    config["target_host"] = "localhost:7233"
    client = await Client.connect(**config)

    # Run a worker for the workflow
    worker = Worker(
        client,
        task_queue="resource_pool-task-queue",
        workflows=[ResourcePoolWorkflow, ResourceUserWorkflow],
        activities=[
            use_resource,
        ],
    )

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
