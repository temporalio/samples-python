import asyncio
from datetime import datetime, timedelta

from temporalio.client import Client, ScheduleBackfill, ScheduleOverlapPolicy
from temporalio.envconfig import ClientConfig

from util import get_temporal_config_path


async def main():
    config = ClientConfig.load_client_connect_config(
        config_file=str(get_temporal_config_path())
    )

    client = await Client.connect(**config)
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
