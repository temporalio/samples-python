import asyncio

from temporalio.client import Client
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

    await handle.pause(note="Pausing the schedule for now")


if __name__ == "__main__":
    asyncio.run(main())
