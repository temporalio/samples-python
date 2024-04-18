"""Module defines temporal worker."""

import asyncio

from shared import DATA_TRANSFORMATION_TASK_QUEUE_NAME
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import (
    SandboxedWorkflowRunner,
    SandboxRestrictions,
)
from workflows import ProtoToParquet

from export_proto_to_parquet.activities import ExportS3Activities


async def main() -> None:
    """Main worker function."""
    # Create client connected to server at the given address
    client: Client = await Client.connect("localhost:7233", namespace="default")

    # Run the worker
    s3_activities = ExportS3Activities()
    worker: Worker = Worker(
        client,
        task_queue=DATA_TRANSFORMATION_TASK_QUEUE_NAME,
        workflows=[ProtoToParquet],
        activities=[s3_activities.get_object_keys, s3_activities.data_trans_and_land],
        workflow_runner=SandboxedWorkflowRunner(
            restrictions=SandboxRestrictions.default.with_passthrough_modules("boto3")
        ),
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
