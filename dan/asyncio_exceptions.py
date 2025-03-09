import asyncio


async def fallable_task():
    await asyncio.sleep(1)
    0 / 0


async def main():
    print("hello")
    task1 = asyncio.create_task(fallable_task())
    task2 = asyncio.create_task(fallable_task())
    await asyncio.gather(task1, task2)


if __name__ == "__main__":
    asyncio.run(main())
