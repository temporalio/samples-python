"""Run one scripted conversation with native Temporal S3 External Storage."""

import asyncio
import hashlib
import uuid

from langchain_core.messages import AIMessage
from temporalio.converter import DataConverter
from temporalio.deepagents import DeepAgentsPlugin
from temporalio.deepagents.testing import mock_model_provider
from temporalio.worker import Worker

from deepagents_plugin.external_storage.client import connect_client
from deepagents_plugin.external_storage.workflow import (
    PAYLOAD_BYTES,
    TASK_QUEUE,
    ExternalStorageAgent,
)


def create_plugin(data_converter: DataConverter) -> DeepAgentsPlugin:
    """Script the model so the demo needs no LLM provider or API key."""
    return DeepAgentsPlugin(
        data_converter=data_converter,
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
                AIMessage(content="I received the complete document."),
                AIMessage(content="The project is called Cedar."),
                AIMessage(content="Cedar uses Python."),
                AIMessage(content="Cedar is due Friday."),
                AIMessage(content="Cedar is a Python project due Friday."),
            ]
        ),
    )


async def main() -> None:
    questions = [
        "Read large-document.txt and acknowledge receiving it.",
        "I am working on a project called Cedar.",
        "The project uses Python.",
        "It is due Friday.",
        "Remind me of the project name, language, and deadline.",
    ]
    async with connect_client(create_plugin) as client:
        async with Worker(
            client,
            task_queue=TASK_QUEUE,
            workflows=[ExternalStorageAgent],
            max_cached_workflows=0,
        ):
            workflow_id = f"deepagents-external-storage-{uuid.uuid4()}"
            result = await client.execute_workflow(
                ExternalStorageAgent.run,
                questions,
                id=workflow_id,
                task_queue=TASK_QUEUE,
            )

    assert result.tool_result_bytes == PAYLOAD_BYTES
    assert result.tool_result_sha256 == hashlib.sha256(b"x" * PAYLOAD_BYTES).hexdigest()
    print(f"Workflow: {workflow_id}")
    print(
        f"Tool result: {result.tool_result_bytes:,} bytes (6 MiB), integrity verified"
    )
    print(f"Conversation turns: {result.turns}")
    print(f"Final answer: {result.last_answer}")


if __name__ == "__main__":
    asyncio.run(main())
