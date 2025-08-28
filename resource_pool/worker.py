import asyncio
import logging

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from resource_pool.pool_client.resource_pool_workflow import ResourcePoolWorkflow
from resource_pool.resource_user_workflow import ResourceUserWorkflow, use_resource
from util import get_temporal_config_path


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    # Start client
    config = ClientConfig.load_client_connect_config(
        config_file=str(get_temporal_config_path())
    )

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
