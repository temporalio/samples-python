"""Worker v2 for the worker versioning sample."""

import asyncio
import logging

from temporalio.client import Client
from temporalio.common import WorkerDeploymentVersion
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker, WorkerDeploymentConfig

from worker_versioning.activities import some_activity, some_incompatible_activity
from worker_versioning.app import DEPLOYMENT_NAME, TASK_QUEUE
from worker_versioning.workflows import AutoUpgradingWorkflowV1b, PinnedWorkflowV2

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    """Run worker v2."""
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    # Create worker v2
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[AutoUpgradingWorkflowV1b, PinnedWorkflowV2],
        activities=[some_activity, some_incompatible_activity],
        deployment_config=WorkerDeploymentConfig(
            version=WorkerDeploymentVersion(
                deployment_name=DEPLOYMENT_NAME, build_id="2.0"
            ),
            use_worker_versioning=True,
        ),
    )

    logging.info("Starting worker v2 (build 2.0)")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
