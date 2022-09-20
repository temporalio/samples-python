import asyncio
from datetime import datetime
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar, cast

from temporalio import activity

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def auto_heartbeater(fn: F) -> F:
    # We want to ensure that the type hints from the original callable are
    # available via our wrapper, so we use the functools wraps decorator
    @wraps(fn)
    async def wrapper(*args, **kwargs):
        done = asyncio.Event()
        # Heartbeat twice as often as the timeout
        heartbeat_timeout = activity.info().heartbeat_timeout
        if heartbeat_timeout:
            asyncio.create_task(
                heartbeat_every(heartbeat_timeout.total_seconds() / 2, done)
            )
        try:
            return await fn(*args, **kwargs)
        finally:
            done.set()

    return cast(F, wrapper)


async def heartbeat_every(
    delay: float, done_event: asyncio.Event, *details: Any
) -> None:
    # Heartbeat every so often while not cancelled
    while not done_event.is_set():
        try:
            await asyncio.wait_for(done_event.wait(), delay)
        except asyncio.TimeoutError:
            print(f"Heartbeating at {datetime.now()}")
            activity.heartbeat(*details)
