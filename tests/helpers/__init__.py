import asyncio
import time
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import TypeVar

T = TypeVar("T")


async def assert_eventually(
    fn: Callable[[], Awaitable[T]],
    *,
    timeout: timedelta = timedelta(seconds=10),
    interval: timedelta = timedelta(milliseconds=200),
) -> T:
    start_sec = time.monotonic()
    while True:
        try:
            res = await fn()
            return res
        except AssertionError:
            if timedelta(seconds=time.monotonic() - start_sec) >= timeout:
                raise
        await asyncio.sleep(interval.total_seconds())
