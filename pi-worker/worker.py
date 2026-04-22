import asyncio
import logging

from temporalio.client import Client
from temporalio.common import WorkerDeploymentVersion
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker, WorkerDeploymentConfig

from activities import hello_activity
from workflows import TASK_QUEUE, SampleWorkflow

DEPLOYMENT_NAME = "demo-order"
BUILD_ID = "v1"


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    config = ClientConfig.load_client_connect_config()
    client = await Client.connect(**config)
    logging.info("Connected to Temporal Service")

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[SampleWorkflow],
        activities=[hello_activity],
        deployment_config=WorkerDeploymentConfig(
            version=WorkerDeploymentVersion(
                deployment_name=DEPLOYMENT_NAME, build_id=BUILD_ID
            ),
            use_worker_versioning=True,
        ),
    )

    logging.info(
        "Starting pi-worker for deployment '%s' build '%s' on task queue '%s'",
        DEPLOYMENT_NAME,
        BUILD_ID,
        TASK_QUEUE,
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
