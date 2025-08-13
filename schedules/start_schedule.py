import asyncio
from datetime import timedelta

from temporalio.client import (
    Client,
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleIntervalSpec,
    ScheduleSpec,
    ScheduleState,
)
from temporalio.envconfig import ClientConfigProfile
from your_workflows import YourSchedulesWorkflow


async def main():
    config_dict = ClientConfigProfile.load().to_dict()
    config_dict.setdefault("address", "localhost:7233")
    config = ClientConfigProfile.from_dict(config_dict)
    client = await Client.connect(**config.to_client_connect_config())

    await client.create_schedule(
        "workflow-schedule-id",
        Schedule(
            action=ScheduleActionStartWorkflow(
                YourSchedulesWorkflow.run,
                "my schedule arg",
                id="schedules-workflow-id",
                task_queue="schedules-task-queue",
            ),
            spec=ScheduleSpec(
                intervals=[ScheduleIntervalSpec(every=timedelta(minutes=2))]
            ),
            state=ScheduleState(note="Here's a note on my Schedule."),
        ),
    )


if __name__ == "__main__":
    asyncio.run(main())
