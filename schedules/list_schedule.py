import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from util import get_temporal_config_path


async def main() -> None:
    config = ClientConfig.load_client_connect_config(
        config_file=str(get_temporal_config_path())
    )

    client = await Client.connect(**config)

    async for schedule in await client.list_schedules():
        print(f"List Schedule Info: {schedule.info}.")


if __name__ == "__main__":
    asyncio.run(main())
