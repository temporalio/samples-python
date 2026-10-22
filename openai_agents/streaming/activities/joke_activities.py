from __future__ import annotations

import random

from temporalio import activity


@activity.defn
async def how_many_jokes() -> int:
    """Return a random integer of jokes to tell between 1 and 10 (inclusive)."""
    return random.randint(1, 10)
