import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig


async def main():
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    handle = client.get_schedule_handle(
        "workflow-schedule-id",
    )

    await handle.pause(note="Pausing the schedule for now")


if __name__ == "__main__":
    asyncio.run(main())
