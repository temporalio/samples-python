import asyncio

from agentcore_worker import ActivityTracker


async def test_activity_tracker_returns_after_idle_debounce() -> None:
    tracker = ActivityTracker()

    await asyncio.wait_for(tracker.wait_until_idle(0.001), timeout=1)
