import asyncio
import logging

from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile
from temporalio.worker import Worker

from resource_pool.pool_client.resource_pool_workflow import ResourcePoolWorkflow
from resource_pool.resource_user_workflow import ResourceUserWorkflow, use_resource


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    # Start client
    config_dict = ClientConfigProfile.load().to_dict()
    config_dict.setdefault("address", "localhost:7233")
    config = ClientConfigProfile.from_dict(config_dict)
    client = await Client.connect(**config.to_client_connect_config())

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
