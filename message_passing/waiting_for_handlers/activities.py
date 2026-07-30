import asyncio

from temporalio import activity


@activity.defn
async def activity_executed_by_update_handler():
    await asyncio.sleep(1)
