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

from batch_daily.workflows import (
    RecordBatchProcessor,
    RecordBatchProcessorWorkflowInput,
    TASK_QUEUE_NAME,
)


async def main() -> None:
    """Main function to run temporal workflow."""
    client = await Client.connect("localhost:7233")

    try:
        wf_input = RecordBatchProcessorWorkflowInput(record_filter="taste=yummy")
        await client.create_schedule(
            "daily-batch-wf-schedule",
            Schedule(
                action=ScheduleActionStartWorkflow(
                    RecordBatchProcessor.run,
                    wf_input,
                    id=f"record-filter-{wf_input.record_filter}",
                    task_queue=TASK_QUEUE_NAME,
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
