import asyncio
import time

import trio
import trio_asyncio
from temporalio import activity


# An asyncio-based async activity
@activity.defn
async def say_hello_activity_async(name: str) -> str:
    # Demonstrate a sleep in both asyncio and Trio, showing that both asyncio
    # and Trio primitives can be used

    # First asyncio
    activity.logger.info("Sleeping in asyncio")
    await asyncio.sleep(0.1)

    # Now Trio. We have to invoke the function separately decorated.
    # We cannot use the @trio_as_aio decorator on the activity itself because
    # it doesn't use functools wrap or similar so it doesn't respond to things
    # like __name__ that @activity.defn needs.
    return await say_hello_in_trio_from_asyncio(name)


@trio_asyncio.trio_as_aio
async def say_hello_in_trio_from_asyncio(name: str) -> str:
    activity.logger.info("Sleeping in Trio (from asyncio)")
    await trio.sleep(0.1)
    return f"Hello, {name}! (from asyncio)"


# A thread-based sync activity
@activity.defn
def say_hello_activity_sync(name: str) -> str:
    # Demonstrate a sleep in both threaded and Trio, showing that both
    # primitives can be used

    # First, thread-blocking
    activity.logger.info("Sleeping normally")
    time.sleep(0.1)

    # Now Trio. We have to use Trio's thread sync tools to run trio calls from
    # a different thread.
    return trio.from_thread.run(say_hello_in_trio_from_sync, name)


async def say_hello_in_trio_from_sync(name: str) -> str:
    activity.logger.info("Sleeping in Trio (from thread)")
    await trio.sleep(0.1)
    return f"Hello, {name}! (from thread)"
