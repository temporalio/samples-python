"""Run a Temporal Worker on a Google Cloud Run worker pool.

``CloudRunIdPlugin`` sets the client identity from Cloud Run instance metadata;
the worker runs until Cloud Run sends SIGTERM (for example, on scale-down).
"""

from __future__ import annotations

import asyncio
import signal

from temporalio.client import Client
from temporalio.contrib.gcp.cloud_run.id import (
    CloudRunIdPlugin,
    get_google_cloud_run_metadata,
)
from temporalio.worker import Worker

from gcp.cloud_run.id.activities import compose_greeting
from gcp.cloud_run.id.settings import load_settings
from gcp.cloud_run.id.workflows import GreetingWorkflow


async def main() -> None:
    settings = load_settings()

    # The plugin reads Cloud Run metadata at connect time, sets the client
    # identity to <instance_id>@<revision>, and propagates it to the worker.
    # @@@SNIPSTART python-cloud-run-id
    client = await Client.connect(
        settings.address,
        namespace=settings.namespace,
        plugins=[CloudRunIdPlugin()],
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

    metadata = get_google_cloud_run_metadata()
    print(
        "Worker starting "
        f"identity={metadata.identity} "
        f"task_queue={settings.task_queue}",
        flush=True,
    )
    await worker.run()
    print("Worker stopped", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
