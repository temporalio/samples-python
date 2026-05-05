import asyncio
import os
import random

from temporalio import activity

COIN_TOSS_VOTE_KEY = "fire"


def _coin_toss_crash_probability() -> float:
    raw = os.environ.get("COIN_TOSS_CRASH_PROBABILITY", "").strip()
    if not raw:
        return 0.5
    try:
        return float(raw)
    except ValueError:
        return 0.5


COIN_TOSS_CRASH_PROBABILITY = _coin_toss_crash_probability()


def is_coin_toss_vote(label: str) -> bool:
    return label.strip().lower() == COIN_TOSS_VOTE_KEY

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

@activity.defn
async def process_vote_activity(label: str) -> dict:
    normalized = label.strip()
    is_coin_toss = is_coin_toss_vote(normalized)
    info = activity.info()

    if is_coin_toss and random.random() < COIN_TOSS_CRASH_PROBABILITY:
        activity.logger.warning(
            "Coin toss vote %r crashed worker on attempt %s",
            normalized,
            info.attempt,
        )
        os._exit(1)

    crashes = max(0, info.attempt - 1) if is_coin_toss else 0
    activity.logger.info(
        "Processed vote %r coin_toss=%s crashes=%s attempt=%s",
        normalized,
        is_coin_toss,
        crashes,
        info.attempt,
    )
    return {"label": normalized, "coin_toss": is_coin_toss, "crashes": crashes}