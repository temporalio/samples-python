"""Run a long-lived Temporal worker on a Google Cloud Run worker pool.

The worker derives its identity and a PINNED Worker Deployment version from
Cloud Run instance metadata using
``temporalio.contrib.gcp.cloud_run.get_google_cloud_run_metadata`` and runs
until Cloud Run sends SIGTERM (for example, on scale-down).
"""

from __future__ import annotations

import asyncio
import signal

from activities import compose_greeting
from settings import load_settings
from temporalio.client import Client
from temporalio.contrib.gcp.cloud_run import get_google_cloud_run_metadata
from temporalio.worker import Worker
from workflows import GreetingWorkflow


async def main() -> None:
    settings = load_settings()

    # Reads CLOUD_RUN_WORKER_POOL/CLOUD_RUN_REVISION (worker pools) or
    # K_SERVICE/K_REVISION (services) and fetches this instance's unique id from
    # the Cloud Run metadata server. Raises if not running on Cloud Run.
    metadata = get_google_cloud_run_metadata()

    client = await Client.connect(
        settings.address,
        namespace=settings.namespace,
        # <instance_id>@<revision>, so each running container is identifiable.
        identity=metadata.worker_identity,
        api_key=settings.api_key,
        tls=settings.tls,
    )

    worker = Worker(
        client,
        task_queue=settings.task_queue,
        workflows=[GreetingWorkflow],
        activities=[compose_greeting],
        # Enables Worker Versioning: deployment name = worker-pool name, build
        # id = Cloud Run revision, with a PINNED default versioning behavior.
        deployment_config=metadata.worker_deployment_config,
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

    version = metadata.worker_deployment_version
    print(
        "Worker starting "
        f"identity={metadata.worker_identity} "
        f"deployment={version.deployment_name} "
        f"build_id={version.build_id} "
        f"task_queue={settings.task_queue}",
        flush=True,
    )
    await worker.run()
    print("Worker stopped", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
