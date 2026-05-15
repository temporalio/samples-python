import asyncio
import logging

from temporalio.client import Client
from temporalio.common import WorkerDeploymentVersion
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker, WorkerDeploymentConfig

from activities import record_response
from models import AGGREGATOR_TASK_QUEUE, TASK_QUEUE
from workflows import PollAggregatorWorkflow

DEPLOYMENT_NAME = "survey-poll-SA"
BUILD_ID = "v1"


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    config = ClientConfig.load_client_connect_config()
    client = await Client.connect(**config)
    logging.info("Connected to Temporal Service")

    deployment_config = WorkerDeploymentConfig(
        version=WorkerDeploymentVersion(
            deployment_name=DEPLOYMENT_NAME, build_id=BUILD_ID
        ),
        use_worker_versioning=True,
    )

    # Activity-only worker for the response queue. Votes are now standalone
    # activities invoked directly by the client (no per-respondent workflow).
    response_worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        activities=[record_response],
        # Testing: cap at a single concurrent activity so any parallel load
        # immediately creates task queue backlog and forces overflow to the
        # serverless Lambda worker. Revert to default (100) for normal operation.
        max_concurrent_activities=1,
        deployment_config=deployment_config,
    )

    # Aggregator runs on a dedicated queue that the Lambda worker does not
    # poll -- the aggregator is long-lived and must not be scheduled onto a
    # function with a ~15-min timeout.
    aggregator_worker = Worker(
        client,
        task_queue=AGGREGATOR_TASK_QUEUE,
        workflows=[PollAggregatorWorkflow],
        deployment_config=deployment_config,
    )

    logging.info(
        "Starting survey-poll workers: deployment='%s' build='%s' queues=['%s', '%s']",
        DEPLOYMENT_NAME,
        BUILD_ID,
        TASK_QUEUE,
        AGGREGATOR_TASK_QUEUE,
    )
    await asyncio.gather(response_worker.run(), aggregator_worker.run())


if __name__ == "__main__":
    asyncio.run(main())
