"""Start the sample Workflow against Temporal Cloud."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from uuid import uuid4

from temporalio.client import Client

from gcp_open_telemetry.workflow import GreetingWorkflow


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} must be set to a non-empty value")
    return value


def _read_api_key() -> str:
    value = os.environ.get("TEMPORAL_API_KEY", "").strip()
    if value:
        return value

    path = os.environ.get("TEMPORAL_API_KEY_FILE", "").strip()
    if not path:
        raise RuntimeError("TEMPORAL_API_KEY or TEMPORAL_API_KEY_FILE must be set")
    value = Path(path).read_text(encoding="utf-8").strip()
    if not value:
        raise RuntimeError("TEMPORAL_API_KEY_FILE must contain a non-empty value")
    return value


async def main() -> None:
    namespace = _required("TEMPORAL_NAMESPACE")
    address = os.environ.get(
        "TEMPORAL_ADDRESS", f"{namespace}.tmprl.cloud:7233"
    ).strip()
    task_queue = _required("TEMPORAL_TASK_QUEUE")
    client = await Client.connect(
        address,
        namespace=namespace,
        api_key=_read_api_key(),
        tls=True,
    )

    workflow_id = f"gcp-open-telemetry-{uuid4()}"
    result = await client.execute_workflow(
        GreetingWorkflow.run,
        "Temporal",
        id=workflow_id,
        task_queue=task_queue,
    )
    print(f"Workflow {workflow_id} result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
