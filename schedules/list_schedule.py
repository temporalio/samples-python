import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile


async def main() -> None:
    config = ClientConfigProfile.load()
    config["address"] = "localhost:7233"
    client = await Client.connect(**config.to_client_connect_config())

    async for schedule in await client.list_schedules():
        print(f"List Schedule Info: {schedule.info}.")


if __name__ == "__main__":
    asyncio.run(main())
