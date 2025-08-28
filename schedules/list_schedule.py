import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig


async def main() -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    async for schedule in await client.list_schedules():
        print(f"List Schedule Info: {schedule.info}.")


if __name__ == "__main__":
    asyncio.run(main())
