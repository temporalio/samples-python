import asyncio

from temporalio.client import Client


async def main() -> None:
    client = await Client.connect("localhost:7233")

    async for schedule in await client.list_schedules():
        print(f"List Schedule Info: {schedule.info}.")


if __name__ == "__main__":
    asyncio.run(main())
