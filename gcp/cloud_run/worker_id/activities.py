"""Activity used by the Cloud Run worker sample."""

from __future__ import annotations

from temporalio import activity


@activity.defn
async def compose_greeting(name: str) -> str:
    activity.logger.info("Composing greeting for %s", name)
    return f"Hello, {name}!"
