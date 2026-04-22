import asyncio
import os

from temporalio import activity


@activity.defn
async def hello_activity(name: str) -> str:
    activity.logger.info("HelloActivity started with name: %s", name)
    greeting = f"Hello, {name}!"
    iterations = int(os.environ.get("HELLO_ITERATIONS") or "30")

    info = activity.info()
    start = int(info.heartbeat_details[0]) if info.heartbeat_details else 0
    if start > 0:
        activity.logger.info("Resuming from iteration %d/%d", start + 1, iterations)

    for i in range(start, iterations):
        print(f"[{i + 1}/{iterations}] {greeting}", flush=True)
        activity.heartbeat(i + 1)
        if i < iterations - 1:
            await asyncio.sleep(5)
    return f"{greeting} (printed {iterations} times)"
