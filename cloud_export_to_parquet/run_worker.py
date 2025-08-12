import asyncio
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import (
    SandboxedWorkflowRunner,
    SandboxRestrictions,
)

from cloud_export_to_parquet.data_trans_activities import (
    data_trans_and_land,
    get_object_keys,
)
from cloud_export_to_parquet.workflows import ProtoToParquet


async def main() -> None:
    """Main worker function."""
    # Create client connected to server at the given address
        # Get repo root - 1 level deep from root
        repo_root = Path(__file__).resolve().parent.parent
        config_file = repo_root / "temporal.toml"
    config = ClientConfig.load_client_connect_config(config_file=str(config_file))
    config["target_host"] = "localhost:7233"
    client = await Client.connect(**config)

    # Run the worker
    worker: Worker = Worker(
        client,
        task_queue="DATA_TRANSFORMATION_TASK_QUEUE",
        workflows=[ProtoToParquet],
        activities=[get_object_keys, data_trans_and_land],
        workflow_runner=SandboxedWorkflowRunner(
            restrictions=SandboxRestrictions.default.with_passthrough_modules("boto3")
        ),
        activity_executor=ThreadPoolExecutor(100),
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
