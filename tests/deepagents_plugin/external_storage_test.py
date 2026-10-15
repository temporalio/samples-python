"""Verify complete S3 transcripts without full-history activity inputs."""

import uuid
from collections.abc import Iterator
from datetime import timedelta

import boto3
import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from moto.server import ThreadedMotoServer
from temporalio.api.enums.v1 import EventType
from temporalio.api.sdk.v1 import ExternalStorageReference
from temporalio.client import Client
from temporalio.converter import DataConverter
from temporalio.deepagents import DeepAgentsPlugin
from temporalio.worker import Replayer, Worker

from deepagents_plugin.external_storage import storage
from deepagents_plugin.external_storage.client import S3_BUCKET, connect_client
from deepagents_plugin.external_storage.storage import (
    CONTEXT_MESSAGES,
    ConversationModel,
)
from deepagents_plugin.external_storage.workflow import (
    PAYLOAD_BYTES,
    ExternalStorageAgent,
)
from tests.deepagents_plugin.helpers import (
    INVOKE_MODEL,
    INVOKE_TOOL,
    count_scheduled_activities,
)


@pytest.fixture
def s3_endpoint() -> Iterator[str]:
    server = ThreadedMotoServer(ip_address="127.0.0.1", port=0, verbose=False)
    server.start()
    try:
        host, port = server.get_host_and_port()
        endpoint = f"http://{host}:{port}"
        s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id="test",
            aws_secret_access_key="test",
            region_name="us-east-1",
        )
        s3.create_bucket(Bucket=S3_BUCKET)
        yield endpoint
    finally:
        server.stop()


@pytest.mark.parametrize("extra_turns", [0, 20])
async def test_external_storage(
    client: Client, s3_endpoint: str, extra_turns: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    queue = f"deepagents-storage-{uuid.uuid4()}"
    target_host = client.service_client.config.target_host
    questions = [
        "Read large-document.txt and acknowledge receiving it.",
        "I am working on a project called Cedar.",
        "The project uses Python.",
        "It is due Friday.",
        "Remind me of the project name, language, and deadline.",
        *[f"Follow-up message {index}." for index in range(extra_turns)],
    ]
    contexts: list[list[BaseMessage]] = []
    scripted_reply = storage.scripted_reply

    def record_context(messages: list[BaseMessage]) -> AIMessage:
        contexts.append(messages)
        return scripted_reply(messages)

    monkeypatch.setattr(storage, "scripted_reply", record_context)
    async with connect_client(target_host=target_host, s3_endpoint=s3_endpoint) as (
        stored_client,
        transcripts,
    ):
        async with Worker(
            stored_client,
            task_queue=queue,
            workflows=[ExternalStorageAgent],
            max_cached_workflows=0,
        ):
            handle = await stored_client.start_workflow(
                ExternalStorageAgent.run,
                questions,
                id=queue,
                task_queue=queue,
                execution_timeout=timedelta(seconds=90),
            )
            result = await handle.result()
            history = await handle.fetch_history()

        assert result.tool_result_bytes == PAYLOAD_BYTES
        assert result.turns == len(questions)
        assert result.last_answer == (
            "Acknowledged." if extra_turns else "Cedar is a Python project due Friday."
        )
        assert result.message_count == 2 * len(questions) + 2
        counts = await count_scheduled_activities(handle)
        assert counts[INVOKE_MODEL] == len(questions) + 1
        assert counts[INVOKE_TOOL] == 1
        assert all(len(context) <= CONTEXT_MESSAGES for context in contexts)
        if extra_turns:
            assert questions[0] not in [m.content for m in contexts[-1]]

        messages = await transcripts.read(
            result.conversation_id, 0, result.message_count
        )
        assert [m.content for m in messages if m.type == "human"] == questions
        assert [m.type for m in messages[:4]] == ["human", "ai", "tool", "ai"]
        assert isinstance(messages[1], AIMessage)
        assert messages[1].tool_calls[0]["name"] == "read_file"
        assert messages[2].content == "x" * PAYLOAD_BYTES
        objects = await transcripts.client.list_objects_v2(
            Bucket=S3_BUCKET, Prefix=f"conversations/{result.conversation_id}/"
        )
        contents = objects["Contents"]
        assert len(contents) == result.message_count
        assert sum(obj["Size"] for obj in contents) < PAYLOAD_BYTES + 50_000

        scheduled = {
            event.event_id: event.activity_task_scheduled_event_attributes
            for event in history.events
            if event.event_type == EventType.EVENT_TYPE_ACTIVITY_TASK_SCHEDULED
        }
        tool_result = next(
            event.activity_task_completed_event_attributes.result.payloads[0]
            for event in history.events
            if event.event_type == EventType.EVENT_TYPE_ACTIVITY_TASK_COMPLETED
            and scheduled[
                event.activity_task_completed_event_attributes.scheduled_event_id
            ].activity_type.name
            == INVOKE_TOOL
        )
        model_inputs = [
            attrs.input.payloads[0]
            for attrs in scheduled.values()
            if attrs.activity_type.name == INVOKE_MODEL
        ]
        for payload in [tool_result, model_inputs[1]]:
            reference = DataConverter.default.payload_converter.from_payload(payload)
            assert isinstance(reference, ExternalStorageReference)
            assert reference.driver_name == "aws.s3driver"
            assert payload.ByteSize() < 1024
        for payload in model_inputs[2:]:
            request = (await stored_client.data_converter.decode([payload]))[0]
            assert len(request["messages"]) == 2  # System instructions + latest user.
            assert not isinstance(
                DataConverter.default.payload_converter.from_payload(payload),
                ExternalStorageReference,
            )
        assert "x" * 1024 not in history.to_json()

    async with connect_client(target_host=target_host, s3_endpoint=s3_endpoint) as (
        replay_client,
        fresh_transcripts,
    ):
        assert (
            await fresh_transcripts.read(
                result.conversation_id, 0, result.message_count
            )
            == messages
        )
        # Retry the first request after later turns: reuse the committed reply.
        retry = await ConversationModel(store=fresh_transcripts).ainvoke([messages[0]])
        assert retry == messages[1]
        assert len(contexts) == len(questions) + 1
        await Replayer(
            workflows=[ExternalStorageAgent],
            data_converter=replay_client.data_converter,
            plugins=[DeepAgentsPlugin(data_converter=replay_client.data_converter)],
        ).replay_workflow(history)
        assert len(contexts) == len(questions) + 1


async def test_transcript_messages_are_immutable(
    s3_endpoint: str, client: Client
) -> None:
    async with connect_client(
        target_host=client.service_client.config.target_host, s3_endpoint=s3_endpoint
    ) as (_, transcripts):
        conversation_id = str(uuid.uuid4())
        original = HumanMessage(content="Keep this exact message.")
        assert await transcripts.put(conversation_id, 0, original) == original
        assert await transcripts.put(conversation_id, 0, original) == original
        assert (
            await transcripts.put(
                conversation_id, 0, HumanMessage(content="Different.")
            )
            == original
        )
        assert await transcripts.read(conversation_id, 0, 1) == [original]
