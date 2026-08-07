from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta

from temporalio import activity, workflow

TASK_QUEUE = "custom-worker-tuner"


@dataclass
class BatchInput:
    activities: int
    seconds: float


@activity.defn
async def do_work(seconds: float) -> None:
    """Sleep, simulating an I/O-bound activity."""
    await asyncio.sleep(seconds)


@workflow.defn
class RunBatch:
    """Runs N do_work activities in parallel."""

    @workflow.run
    async def run(self, inp: BatchInput) -> None:
        await asyncio.gather(
            *(
                workflow.execute_activity(
                    do_work,
                    inp.seconds,
                    start_to_close_timeout=timedelta(minutes=2),
                )
                for _ in range(inp.activities)
            )
        )
