"""Run a long-lived Temporal worker on a Google Cloud Run worker pool.

The worker registers ``temporalio.contrib.gcp.cloud_run.WorkerIDPlugin`` on the
client. The plugin reads Cloud Run instance metadata and automatically sets the
client identity and a PINNED Worker Deployment version, then propagates to the
worker. The worker runs until Cloud Run sends SIGTERM (for example, on
scale-down).
"""

from __future__ import annotations

import asyncio
import signal

from activities import compose_greeting
from settings import load_settings
from temporalio.client import Client
from temporalio.contrib.gcp.cloud_run import WorkerIDPlugin
from temporalio.worker import Worker
from workflows import GreetingWorkflow


async def main() -> None:
    settings = load_settings()

    # The plugin reads CLOUD_RUN_WORKER_POOL/CLOUD_RUN_REVISION (worker pools) or
    # K_SERVICE/K_REVISION (services), fetches this instance's unique id from the
    # Cloud Run metadata server at connect time, and raises if not running on
    # Cloud Run. It sets the client identity to <instance_id>@<revision> (so each
    # running container is identifiable) and configures the worker with a
    # deployment config that enables Worker Versioning -- deployment name =
    # worker-pool name, build id = Cloud Run revision -- with a PINNED default
    # versioning behavior. Client plugins propagate to workers automatically.
    client = await Client.connect(
        settings.address,
        namespace=settings.namespace,
        plugins=[WorkerIDPlugin()],
        api_key=settings.api_key,
        tls=settings.tls,
    )

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

    # identity was set by WorkerIDPlugin from Cloud Run instance metadata.
    print(
        "Worker starting "
        f"identity={client.identity} "
        f"task_queue={settings.task_queue}",
        flush=True,
    )
    await worker.run()
    print("Worker stopped", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
