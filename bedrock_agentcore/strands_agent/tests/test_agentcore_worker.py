import asyncio

from agentcore_worker import WorkTracker


async def test_work_tracker_returns_after_idle_debounce() -> None:
    tracker = WorkTracker()

    await asyncio.wait_for(tracker.wait_until_idle(0.001), timeout=1)


async def test_work_tracker_waits_for_inflight_work() -> None:
    tracker = WorkTracker()
    tracker.begin()

    waiter = asyncio.create_task(tracker.wait_until_idle(0.001))
    await asyncio.sleep(0.05)
    assert not waiter.done()

    tracker.end()
    await asyncio.wait_for(waiter, timeout=1)
