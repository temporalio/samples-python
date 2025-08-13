import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile


async def main():
    config_dict = ClientConfigProfile.load().to_dict()
    config_dict.setdefault("address", "localhost:7233")
    config = ClientConfigProfile.from_dict(config_dict)
    client = await Client.connect(**config.to_client_connect_config())

    handle = client.get_schedule_handle(
        "workflow-schedule-id",
    )

    await handle.pause(note="Pausing the schedule for now")


if __name__ == "__main__":
    asyncio.run(main())
