import asyncio
from datetime import datetime, timedelta

from temporalio.client import Client, ScheduleBackfill, ScheduleOverlapPolicy


async def main():
    client = await Client.connect("localhost:7233")
    handle = client.get_schedule_handle(
        "workflow-schedule-id",
    )
    now = datetime.utcnow()
    if now.second == 0:
        now += timedelta(seconds=1)
    await handle.backfill(
        ScheduleBackfill(
            start_at=now,
            end_at=now,
            overlap=ScheduleOverlapPolicy.ALLOW_ALL,
        ),
    )

    print(f"Result: {handle}")


if __name__ == "__main__":
    asyncio.run(main())
