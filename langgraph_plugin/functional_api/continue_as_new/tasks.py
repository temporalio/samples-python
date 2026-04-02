"""Continue-as-New Task Definitions.

Tasks that demonstrate caching across continue-as-new boundaries.
Each task tracks execution count to verify caching works correctly.
"""

import logging

from langgraph.func import task

logger = logging.getLogger(__name__)


@task
def step_1(x: int) -> int:
    """Step 1: multiply by 2.

    This task logs when it executes to help verify caching.
    """
    logger.info(f"step_1 executing with input {x}")
    return x * 2


@task
def step_2(x: int) -> int:
    """Step 2: add 5."""
    logger.info(f"step_2 executing with input {x}")
    return x + 5


@task
def step_3(x: int) -> int:
    """Step 3: multiply by 3."""
    logger.info(f"step_3 executing with input {x}")
    return x * 3


@task
def step_4(x: int) -> int:
    """Step 4: subtract 10."""
    logger.info(f"step_4 executing with input {x}")
    return x - 10


@task
def step_5(x: int) -> int:
    """Step 5: add 100."""
    logger.info(f"step_5 executing with input {x}")
    return x + 100
