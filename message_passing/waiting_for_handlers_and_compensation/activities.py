import asyncio

from temporalio import activity


@activity.defn
async def activity_executed_by_update_handler():
    await asyncio.sleep(1)


@activity.defn
async def activity_executed_by_update_handler_to_perform_compensation():
    await asyncio.sleep(1)
