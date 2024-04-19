import asyncio

from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import (
    SandboxedWorkflowRunner,
    SandboxRestrictions,
)
from workflows import ProtoToParquet

from cloud_export_to_parquet.data_trans_activities import (
    data_trans_and_land,
    get_object_keys,
)


async def main() -> None:
    """Main worker function."""
    # Create client connected to server at the given address
    client = await Client.connect("localhost:7233")

    # Run the worker
    worker: Worker = Worker(
        client,
        task_queue="DATA_TRANSFORMATION_TASK_QUEUE",
        workflows=[ProtoToParquet],
        activities=[get_object_keys, data_trans_and_land],
        workflow_runner=SandboxedWorkflowRunner(
            restrictions=SandboxRestrictions.default.with_passthrough_modules("boto3")
        ),
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
