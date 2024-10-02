import asyncio

from temporalio import activity


@activity.defn
async def my_activity():
    await asyncio.sleep(1)
