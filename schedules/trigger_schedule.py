import asyncio

from temporalio.client import Client


async def main():
    client = await Client.connect("localhost:7233")
    handle = client.get_schedule_handle(
        "workflow-schedule-id",
    )

    await handle.trigger()


if __name__ == "__main__":
    asyncio.run(main())
