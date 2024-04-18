"""Module defines run temporal workflow."""

import asyncio
import traceback
from datetime import datetime, timedelta

from dataobject import ProtoToParquetWorkflowInput
from shared import DATA_TRANSFORMATION_TASK_QUEUE_NAME, WORKFLOW_ID_PREFIX
from temporalio.client import (
    Client,
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleIntervalSpec,
    ScheduleSpec,
    WorkflowFailureError,
)
from workflows import ProtoToParquet


async def main() -> None:
    """Main function to run temporal workflow."""
    # Create client connected to server at the given address
    client: Client = await Client.connect("localhost:7233", namespace="default")
    # TODO: update s3_bucket and namespace to the actual name
    wf_input = ProtoToParquetWorkflowInput(
        num_delay_hour=2,
        export_s3_bucket="test-input-bucket",
        namespace="test.namespace",
        output_s3_bucket="test-output-bucket",
    )

    try:
        await client.create_schedule(
            "hourly-proto-to-parquet-wf-schedule",
            Schedule(
                action=ScheduleActionStartWorkflow(
                    ProtoToParquet.run,
                    wf_input,
                    id=f"{WORKFLOW_ID_PREFIX}-{datetime.now()}",
                    task_queue=DATA_TRANSFORMATION_TASK_QUEUE_NAME,
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
