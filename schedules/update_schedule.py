import asyncio
from datetime import timedelta

from temporalio.client import Client, ScheduleUpdate, ScheduleUpdateInput


async def main():
    client = await Client.connect("localhost:7233")
    handle = client.get_schedule_handle(
        "workflow-schedule-id",
    )

    async def update_schedule_simple(
        input: ScheduleUpdateInput, timeout_minutes: int = 7
    ) -> ScheduleUpdate:
        schedule_action = input.description.schedule.action
        schedule_action.task_timeout = timedelta(minutes=timeout_minutes)
        schedule_action.args = ["my new schedule arg"]

        return ScheduleUpdate(schedule=input.description.schedule)

    await handle.update(update_schedule_simple)
    await handle.trigger()

    async def schedule_count() -> int:
        return len([i async for i in await client.list_schedules()])

    print(f"Schedule count: {await schedule_count()}")


if __name__ == "__main__":
    asyncio.run(main())
