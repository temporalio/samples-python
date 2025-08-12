import asyncio
import traceback
from datetime import datetime, timedelta

from temporalio.client import (
    Client,
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleIntervalSpec,
    ScheduleSpec,
    WorkflowFailureError,
)

from cloud_export_to_parquet.workflows import (
    ProtoToParquet,
    ProtoToParquetWorkflowInput,
)


async def main() -> None:
    """Main function to run temporal workflow."""
    # Create client connected to server at the given address
        # Get repo root - 1 level deep from root
        repo_root = Path(__file__).resolve().parent.parent
        config_file = repo_root / "temporal.toml"
    config = ClientConfig.load_client_connect_config(config_file=str(config_file))
    config["target_host"] = "localhost:7233"
    client = await Client.connect(**config)
    # TODO: update s3_bucket and namespace to the actual usecase
    wf_input = ProtoToParquetWorkflowInput(
        num_delay_hour=2,
        export_s3_bucket="test-input-bucket",
        namespace="test.namespace",
        output_s3_bucket="test-output-bucket",
    )

    # Run the workflow
    # try:
    #     await client.start_workflow(
    #         ProtoToParquet.run,
    #         wf_input,
    #         id = f"proto-to-parquet-{datetime.now()}",
    #         task_queue="DATA_TRANSFORMATION_TASK_QUEUE",
    #     )
    # except WorkflowFailureError:
    #     print("Got exception: ", traceback.format_exc())

    # Create the schedule
    try:
        await client.create_schedule(
            "hourly-proto-to-parquet-wf-schedule",
            Schedule(
                action=ScheduleActionStartWorkflow(
                    ProtoToParquet.run,
                    wf_input,
                    id=f"proto-to-parquet-{datetime.now()}",
                    task_queue="DATA_TRANSFORMATION_TASK_QUEUE",
                ),
                spec=ScheduleSpec(
                    intervals=[ScheduleIntervalSpec(every=timedelta(hours=1))]
                ),
            ),
        )
    except WorkflowFailureError:
        print("Got exception: ", traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(main())
