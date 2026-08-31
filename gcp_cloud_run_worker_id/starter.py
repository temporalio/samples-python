"""Start a GreetingWorkflow on the Cloud Run worker's task queue.

Run this locally against the same Temporal service the worker connects to, using
the same TEMPORAL_* environment variables.
"""

from __future__ import annotations

import asyncio

from settings import load_settings
from temporalio.client import Client
from workflows import GreetingWorkflow


async def main() -> None:
    settings = load_settings()
    client = await Client.connect(
        settings.address,
        namespace=settings.namespace,
        api_key=settings.api_key,
        tls=settings.tls,
    )

    result = await client.execute_workflow(
        GreetingWorkflow.run,
        "Cloud Run worker pool",
        id="gcp-cloud-run-worker-id-sample",
        task_queue=settings.task_queue,
    )
    print(f"Workflow result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
