from __future__ import annotations

import asyncio
import logging

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import FixedSizeSlotSupplier, Worker, WorkerTuner

from custom_worker_tuner.downstream import Downstream
from custom_worker_tuner.shared import TASK_QUEUE, RunBatch, do_work
from custom_worker_tuner.supplier import DownstreamAwareSupplier

CAPACITY = 10  # number of connections allowed at a time
POLL_INTERVAL_MS = 500
LOG_LEVEL = "INFO"  # flip to "DEBUG" to see every increment/decrement


async def main() -> None:
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s.%(msecs)03d  %(message)s",
        datefmt="%H:%M:%S",
    )

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    downstream = Downstream(allowed_connections=CAPACITY, name="db")
    supplier = DownstreamAwareSupplier(downstream, poll_interval_ms=POLL_INTERVAL_MS)
    tuner = WorkerTuner.create_composite(
        workflow_supplier=FixedSizeSlotSupplier(100),
        activity_supplier=supplier,
        local_activity_supplier=FixedSizeSlotSupplier(100),
        nexus_supplier=FixedSizeSlotSupplier(100),
    )

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[RunBatch],
        activities=[do_work],
        tuner=tuner,
    )

    print(f"\nworker started — capacity={CAPACITY}, poll={POLL_INTERVAL_MS}ms\n")
    print("TIME          EVENT     COUNT   DETAIL")
    print("─" * 60)
    await worker.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
