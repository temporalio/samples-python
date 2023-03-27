import asyncio

from temporalio.client import Client, ScheduleListInfo


async def main() -> None:
    client = await Client.connect("localhost:7233")

    async def list_schedule_simple() -> None:
        async for schedule in await client.list_schedules():
            schedule_info = schedule.info
            if isinstance(schedule_info, ScheduleListInfo):
                print(f"List Schedule Info: {schedule_info}.")

    return await list_schedule_simple()


if __name__ == "__main__":
    asyncio.run(main())
