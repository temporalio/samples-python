from __future__ import annotations

import asyncio
import logging

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import FixedSizeSlotSupplier, Worker, WorkerTuner

from custom_worker_tuner.db_pool import FakeDatabaseConnectionPool
from custom_worker_tuner.shared import TASK_QUEUE, RunBatch, do_work
from custom_worker_tuner.supplier import PoolSlotSupplier

CAPACITY = 10  # number of pool connections (and concurrent activities)
LOG_LEVEL = "INFO"


async def main() -> None:
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s.%(msecs)03d  %(message)s",
        datefmt="%H:%M:%S",
    )

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    pool = FakeDatabaseConnectionPool(allowed_connections=CAPACITY, name="db")
    supplier = PoolSlotSupplier(pool)
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

    print(f"\nworker started — capacity={CAPACITY}\n")
    print("TIME          EVENT     COUNT     QUEUE  DETAIL")
    print("(COUNT shows before→after / capacity; QUEUE = tasks parked waiting)")
    print("─" * 65)
    await worker.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
