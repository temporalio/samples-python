import random

from temporalio import activity


@activity.defn
async def random_number(max_value: int) -> int:
    """Generate a random number up to the provided maximum."""
    return random.randint(0, max_value)


@activity.defn
async def multiply_by_two(x: int) -> int:
    """Simple multiplication by two."""
    return x * 2
