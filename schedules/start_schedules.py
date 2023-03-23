import asyncio

from temporalio.client import (
    Client,
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleCalendarSpec,
    ScheduleRange,
    ScheduleSpec,
    ScheduleState,
)

from your_workflows import YourSchedulesWorkflow


async def main():
    client = await Client.connect("localhost:7233")
    await client.create_schedule(
        "workflow-schedule-id",
        Schedule(
            action=ScheduleActionStartWorkflow(
                YourSchedulesWorkflow.run,
                "my schedule arg",
                id="schedules-workflow-id",
                task_queue="my-task-queue",
            ),
            spec=ScheduleSpec(
                calendars=[
                    ScheduleCalendarSpec(
                        second=(ScheduleRange(1, step=1),),
                        minute=(ScheduleRange(2, 3),),
                        hour=(ScheduleRange(4, 5, 6),),
                        day_of_month=(ScheduleRange(7),),
                        month=(ScheduleRange(9),),
                        year=(ScheduleRange(2080),),
                        # day_of_week=[ScheduleRange(1)],
                        comment="spec comment 1",
                    )
                ],
                # intervals=[
                #    ScheduleIntervalSpec(
                #        every=timedelta(days=10),
                #        offset=timedelta(days=2),
                #    )
                # ],
                # cron_expressions=["0 12 * * MON"],
                # skip=[ScheduleCalendarSpec(year=(ScheduleRange(2050),))],
                # start_at=datetime(2060, 7, 8, 9, 10, 11, tzinfo=timezone.utc),
                # jitter=timedelta(seconds=80),
            ),
            state=ScheduleState(
                note="Here's a note on my Scheduled Workflows", paused=False
            ),
        ),
    ),


if __name__ == "__main__":
    asyncio.run(main())
