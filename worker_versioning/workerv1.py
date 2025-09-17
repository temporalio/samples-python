"""Worker v1 for the worker versioning sample."""

import asyncio
import logging

from temporalio.client import Client
from temporalio.common import WorkerDeploymentVersion
from temporalio.worker import Worker, WorkerDeploymentConfig

from worker_versioning.activities import some_activity, some_incompatible_activity
from worker_versioning.app import DEPLOYMENT_NAME, TASK_QUEUE
from worker_versioning.workflows import AutoUpgradingWorkflowV1, PinnedWorkflowV1

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    """Run worker v1."""
    client = await Client.connect("localhost:7233")

    # Create worker v1
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[AutoUpgradingWorkflowV1, PinnedWorkflowV1],
        activities=[some_activity, some_incompatible_activity],
        deployment_config=WorkerDeploymentConfig(
            version=WorkerDeploymentVersion(
                deployment_name=DEPLOYMENT_NAME, build_id="1.0"
            ),
            use_worker_versioning=True,
        ),
    )

    logging.info("Starting worker v1 (build 1.0)")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
