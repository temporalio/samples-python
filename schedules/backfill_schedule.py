import asyncio
from datetime import datetime, timedelta

from temporalio.client import Client, ScheduleBackfill, ScheduleOverlapPolicy
from temporalio.envconfig import ClientConfigProfile


async def main():
    config = ClientConfigProfile.load()
    config["address"] = "localhost:7233"
    client = await Client.connect(**config.to_client_connect_config())

    handle = client.get_schedule_handle(
        "workflow-schedule-id",
    )
    now = datetime.utcnow()
    await handle.backfill(
        ScheduleBackfill(
            start_at=now - timedelta(minutes=10),
            end_at=now - timedelta(minutes=9),
            overlap=ScheduleOverlapPolicy.ALLOW_ALL,
        ),
    )


if __name__ == "__main__":
    asyncio.run(main())
