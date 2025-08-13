import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile


async def main():
    config = ClientConfigProfile.load()
    config["address"] = "localhost:7233"
    client = await Client.connect(**config.to_client_connect_config())

    handle = client.get_schedule_handle(
        "workflow-schedule-id",
    )

    await handle.delete()


if __name__ == "__main__":
    asyncio.run(main())
