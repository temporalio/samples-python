import asyncio

from temporalio import activity


@activity.defn
async def process_item(item: str) -> str:
    """Long-running activity that heartbeats, and fails its first two attempts.

    The heartbeats + sleep make the activity observably "in flight" so you can
    pause the workflow while it runs. The deliberate failures on the first two
    attempts let you demonstrate `temporal activity pause`, which halts retries.
    """
    info = activity.info()
    activity.logger.info("Processing %s (attempt %d)", item, info.attempt)

    for _ in range(5):
        await asyncio.sleep(1)
        activity.heartbeat()

    if info.attempt < 3:
        raise RuntimeError(f"transient failure on attempt {info.attempt}")

    return f"processed {item}"
