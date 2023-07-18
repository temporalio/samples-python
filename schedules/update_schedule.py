import asyncio

from temporalio.client import (
    Client,
    ScheduleActionStartWorkflow,
    ScheduleUpdate,
    ScheduleUpdateInput,
)


async def main():
    client = await Client.connect("localhost:7233")
    handle = client.get_schedule_handle(
        "workflow-schedule-id",
    )

    async def update_schedule_simple(input: ScheduleUpdateInput) -> ScheduleUpdate:
        schedule_action = input.description.schedule.action

        if isinstance(schedule_action, ScheduleActionStartWorkflow):
            schedule_action.args = ["my new schedule arg"]
        return ScheduleUpdate(schedule=input.description.schedule)

    await handle.update(update_schedule_simple)


if __name__ == "__main__":
    asyncio.run(main())
