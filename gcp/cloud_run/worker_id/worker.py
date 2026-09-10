"""Run a long-lived Temporal worker on a Google Cloud Run worker pool.

The worker registers ``temporalio.contrib.gcp.cloud_run.worker_id.WorkerIDPlugin``
on the client. The plugin reads Cloud Run instance metadata and sets the client
identity to ``<instance_id>@<revision>``, which then propagates to the worker
automatically. The worker runs until Cloud Run sends SIGTERM (for example, on
scale-down).
"""

from __future__ import annotations

import asyncio
import signal

from temporalio.client import Client
from temporalio.contrib.gcp.cloud_run.worker_id import (
    WorkerIDPlugin,
    get_google_cloud_run_metadata,
)
from temporalio.worker import Worker

from gcp.cloud_run.worker_id.activities import compose_greeting
from gcp.cloud_run.worker_id.settings import load_settings
from gcp.cloud_run.worker_id.workflows import GreetingWorkflow


async def main() -> None:
    settings = load_settings()

    # WorkerIDPlugin reads CLOUD_RUN_WORKER_POOL/CLOUD_RUN_REVISION (worker pools)
    # or K_SERVICE/K_REVISION (services), fetches this instance's unique id from
    # the Cloud Run metadata server at connect time, and raises if not running on
    # Cloud Run. It sets the client identity to <instance_id>@<revision> so each
    # running container is identifiable. Client plugins propagate to workers
    # automatically, so there is nothing to wire up on the Worker.
    # @@@SNIPSTART python-cloud-run-worker-id
    client = await Client.connect(
        settings.address,
        namespace=settings.namespace,
        plugins=[WorkerIDPlugin()],
        api_key=settings.api_key,
        tls=settings.tls,
    )
    # @@@SNIPEND

    worker = Worker(
        client,
        task_queue=settings.task_queue,
        workflows=[GreetingWorkflow],
        activities=[compose_greeting],
    )

    loop = asyncio.get_running_loop()
    shutdown_requested = False

    def request_shutdown() -> None:
        nonlocal shutdown_requested
        if shutdown_requested:
            return
        shutdown_requested = True
        print("Worker shutdown requested", flush=True)
        loop.create_task(worker.shutdown())

    for signum in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(signum, request_shutdown)

    # The plugin already applied this identity to the client; read the Cloud Run
    # instance metadata to log the same worker_identity value at startup.
    metadata = get_google_cloud_run_metadata()
    print(
        "Worker starting "
        f"identity={metadata.worker_identity} "
        f"task_queue={settings.task_queue}",
        flush=True,
    )
    await worker.run()
    print("Worker stopped", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
