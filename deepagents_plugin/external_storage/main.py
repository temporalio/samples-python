"""Run an offline agent with native External Storage for a 6 MiB tool result."""

import asyncio
import hashlib
import uuid

from temporalio.worker import Worker

from deepagents_plugin.external_storage.client import connect_client
from deepagents_plugin.external_storage.workflow import (
    PAYLOAD_BYTES,
    ExternalStorageAgent,
)


async def main() -> None:
    workflow_id = f"deepagents-external-storage-{uuid.uuid4()}"
    async with connect_client() as client:
        async with Worker(
            client,
            task_queue=workflow_id,
            workflows=[ExternalStorageAgent],
        ):
            result = await client.execute_workflow(
                ExternalStorageAgent.run,
                "Read large-document.txt and acknowledge receiving it.",
                id=workflow_id,
                task_queue=workflow_id,
            )

    assert result.tool_result_bytes == PAYLOAD_BYTES
    assert result.tool_result_sha256 == hashlib.sha256(b"x" * PAYLOAD_BYTES).hexdigest()
    print(f"Workflow: {workflow_id}")
    print(f"Tool result: {result.tool_result_bytes:,} bytes (6 MiB)")
    print(f"SHA-256: {result.tool_result_sha256}")
    print(f"Final answer: {result.last_answer}")


if __name__ == "__main__":
    asyncio.run(main())
