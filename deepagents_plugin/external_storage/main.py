"""Run an offline conversation with S3 transcripts and large tool payloads."""

import asyncio
import uuid

from temporalio.worker import Worker

from deepagents_plugin.external_storage.client import S3_BUCKET, connect_client
from deepagents_plugin.external_storage.workflow import (
    PAYLOAD_BYTES,
    TASK_QUEUE,
    ExternalStorageAgent,
)


async def main() -> None:
    workflow_id = f"deepagents-external-storage-{uuid.uuid4()}"
    questions = [
        "Read large-document.txt and acknowledge receiving it.",
        "I am working on a project called Cedar.",
        "The project uses Python.",
        "It is due Friday.",
        "Remind me of the project name, language, and deadline.",
    ]
    async with connect_client() as (client, _):
        async with Worker(
            client,
            task_queue=TASK_QUEUE,
            workflows=[ExternalStorageAgent],
        ):
            result = await client.execute_workflow(
                ExternalStorageAgent.run,
                questions,
                id=workflow_id,
                task_queue=TASK_QUEUE,
            )

    assert result.tool_result_bytes == PAYLOAD_BYTES
    print(f"Workflow: {workflow_id}")
    print(f"Tool result: {result.tool_result_bytes:,} bytes (6 MiB)")
    print(
        f"Transcript: s3://{S3_BUCKET}/conversations/"
        f"{result.conversation_id}/ ({result.message_count} messages)"
    )
    print(f"Final answer: {result.last_answer}")


if __name__ == "__main__":
    asyncio.run(main())
