"""Run one Deep Agent with a 6 MiB tool result and native S3 storage.

Both the worker and starter run in this process. The two model replies are
scripted, so the demo needs no LLM credentials or provider context budget.
The model and tool still run as real Temporal activities.
"""

import asyncio
import hashlib
import uuid

from langchain_core.messages import AIMessage
from temporalio.contrib.deepagents import DeepAgentsPlugin
from temporalio.contrib.deepagents.testing import mock_model_provider
from temporalio.worker import Worker

from deepagents_plugin.external_storage.client import connect_client
from deepagents_plugin.external_storage.workflow import (
    PAYLOAD_BYTES,
    TASK_QUEUE,
    ExternalStorageAgent,
)


def create_plugin() -> DeepAgentsPlugin:
    """Script a tool request and acknowledgment for this single-workflow demo."""
    return DeepAgentsPlugin(
        model_provider=mock_model_provider(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "read_file",
                            "args": {"file_path": "large-document.txt"},
                            "id": "call-read",
                        }
                    ],
                ),
                AIMessage(content="Received the complete document."),
            ]
        )
    )


async def main() -> None:
    async with connect_client(create_plugin()) as client:
        async with Worker(
            client,
            task_queue=TASK_QUEUE,
            workflows=[ExternalStorageAgent],
            max_cached_workflows=0,
        ):
            workflow_id = f"deepagents-external-storage-{uuid.uuid4()}"
            result = await client.execute_workflow(
                ExternalStorageAgent.run,
                "Read large-document.txt and acknowledge receiving it.",
                id=workflow_id,
                task_queue=TASK_QUEUE,
            )

        assert result.result_bytes == PAYLOAD_BYTES
        assert result.sha256 == hashlib.sha256(b"x" * PAYLOAD_BYTES).hexdigest()
        print(f"Workflow: {workflow_id}")
        print(f"Tool result: {result.result_bytes:,} bytes (6 MiB), integrity verified")
        print(f"SHA-256: {result.sha256}")
        print(f"Agent: {result.answer}")


if __name__ == "__main__":
    asyncio.run(main())
