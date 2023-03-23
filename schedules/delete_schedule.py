import asyncio

from temporalio.client import Client


async def main():
    client = await Client.connect("localhost:7233")
    handle = client.get_schedule_handle(
        "workflow-schedule-id",
    )
    desc_handle = await handle.describe()
    print(f"{desc_handle.schedule}")

    await handle.delete()
    print(f"State: {desc_handle.schedule.state}")


if __name__ == "__main__":
    asyncio.run(main())
