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

from batch.workflows import (
    DailyBatch,
    DailyBatchWorkflowInput,
)


async def main() -> None:
    """Main function to run temporal workflow."""
    client = await Client.connect("localhost:7233")

    wf_input = DailyBatchWorkflowInput(
        record_filter="taste=yummy",
        # XXX: how do we get the current day in a way that works with the schedule?
        start_day=datetime.now().date().strftime("%Y-%m-%d"),
        end_day=((datetime.now().date()) + timedelta(days=1)).strftime("%Y-%m-%d"),
    )

    try:
        await client.create_schedule(
            "daily-batch-wf-schedule",
            Schedule(
                action=ScheduleActionStartWorkflow(
                    DailyBatch.run,
                    wf_input,
                    id=f"daily-batch-{wf_input.record_filter}",
                    task_queue="TASK_QUEUE",
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
