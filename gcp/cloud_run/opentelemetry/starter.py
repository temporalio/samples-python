"""Start the sample Workflow against the Cloud Run worker's task queue."""

from __future__ import annotations

import asyncio
from uuid import uuid4

from temporalio.client import Client

from gcp.cloud_run.opentelemetry.settings import load_settings
from gcp.cloud_run.opentelemetry.workflow import GreetingWorkflow


async def main() -> None:
    settings = load_settings()
    client = await Client.connect(
        settings.address,
        namespace=settings.namespace,
        api_key=settings.api_key,
        tls=settings.tls,
    )

    workflow_id = f"gcp-cloud-run-{uuid4()}"
    result = await client.execute_workflow(
        GreetingWorkflow.run,
        "Temporal",
        id=workflow_id,
        task_queue=settings.task_queue,
    )
    print(f"Workflow {workflow_id} result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
