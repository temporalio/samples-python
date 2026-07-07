"""
Helper script to start a SampleWorkflow execution against the Cloud Run worker.

Run from the repo root:

    TEMPORAL_ADDRESS=<address> TEMPORAL_NAMESPACE=<namespace> \\
        uv run python -m cloud_run_worker.starter
"""

import asyncio
import os

from temporalio.client import Client, TLSConfig

from cloud_run_worker.workflows import TASK_QUEUE, SampleWorkflow


def _tls_config() -> TLSConfig | None:
    cert_b64 = os.environ.get("TEMPORAL_TLS_CERT")
    key_b64 = os.environ.get("TEMPORAL_TLS_KEY")
    if cert_b64 and key_b64:
        import base64

        return TLSConfig(
            client_cert=base64.b64decode(cert_b64),
            client_private_key=base64.b64decode(key_b64),
        )
    return None


async def main() -> None:
    address = os.environ.get("TEMPORAL_ADDRESS", "localhost:7233")
    namespace = os.environ.get("TEMPORAL_NAMESPACE", "default")
    task_queue = os.environ.get("TEMPORAL_TASK_QUEUE", TASK_QUEUE)

    client = await Client.connect(
        address,
        namespace=namespace,
        tls=_tls_config() or False,
    )
    print(f"Connected to Temporal Service at {address}")

    result = await client.execute_workflow(
        SampleWorkflow.run,
        "Cloud Run Worker!",
        id="cloud-run-workflow-id-1",
        task_queue=task_queue,
    )
    print(f"Workflow result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
