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

    desc = await handle.describe()

    print(f"Returns the note: {desc.schedule.state.note}")


if __name__ == "__main__":
    asyncio.run(main())
