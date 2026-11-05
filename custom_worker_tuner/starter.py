from __future__ import annotations

import asyncio
import time
import uuid

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from custom_worker_tuner.shared import TASK_QUEUE, BatchInput, RunBatch

# Tweak these to push more or less load.
WORKFLOWS = 10
ACTIVITIES_PER_WORKFLOW = 20
SECONDS_PER_ACTIVITY = 2.0


async def main() -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)
    run_id = uuid.uuid4().hex[:8]
    inp = BatchInput(activities=ACTIVITIES_PER_WORKFLOW, seconds=SECONDS_PER_ACTIVITY)
    total = WORKFLOWS * ACTIVITIES_PER_WORKFLOW

    print(
        f"starting {WORKFLOWS} workflows × {ACTIVITIES_PER_WORKFLOW} activities × {SECONDS_PER_ACTIVITY}s"
    )
    t0 = time.perf_counter()

    handles = await asyncio.gather(
        *(
            client.start_workflow(
                RunBatch.run,
                inp,
                id=f"batch-{run_id}-{i}",
                task_queue=TASK_QUEUE,
            )
            for i in range(WORKFLOWS)
        )
    )
    await asyncio.gather(*(h.result() for h in handles))

    wall = time.perf_counter() - t0
    print(f"done in {wall:.1f}s ({total} activities, {total / wall:.0f}/s)")


if __name__ == "__main__":
    asyncio.run(main())
