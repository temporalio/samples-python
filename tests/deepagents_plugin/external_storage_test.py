"""Verify large tool and conversation payloads use native S3 External Storage."""

import hashlib
import uuid
from collections.abc import Iterator
from datetime import timedelta

import boto3
import pytest
from moto.server import ThreadedMotoServer
from temporalio.api.enums.v1 import EventType
from temporalio.api.sdk.v1 import ExternalStorageReference
from temporalio.client import Client
from temporalio.converter import DataConverter
from temporalio.worker import Replayer, Worker

from deepagents_plugin.external_storage.client import S3_BUCKET, connect_client
from deepagents_plugin.external_storage.main import create_plugin
from deepagents_plugin.external_storage.workflow import (
    PAYLOAD_BYTES,
    ExternalStorageAgent,
    ExternalStorageResult,
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


async def test_external_storage(client: Client, s3_endpoint: str) -> None:
    queue = f"deepagents-storage-{uuid.uuid4()}"
    target_host = client.service_client.config.target_host
    questions = [
        "Read large-document.txt and acknowledge receiving it.",
        "I am working on a project called Cedar.",
        "The project uses Python.",
        "It is due Friday.",
        "Remind me of the project name, language, and deadline.",
    ]
    async with connect_client(
        create_plugin, target_host=target_host, s3_endpoint=s3_endpoint
    ) as stored_client:
        assert stored_client.data_converter.external_storage is not None
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
                execution_timeout=timedelta(seconds=60),
            )
            result = await handle.result()
            history = await handle.fetch_history()

        assert result == ExternalStorageResult(
            tool_result_bytes=PAYLOAD_BYTES,
            tool_result_sha256=hashlib.sha256(b"x" * PAYLOAD_BYTES).hexdigest(),
            turns=5,
            last_answer="Cedar is a Python project due Friday.",
        )
        counts = await count_scheduled_activities(handle)
        assert counts[INVOKE_MODEL] == 6
        assert counts[INVOKE_TOOL] == 1

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
        for payload in [tool_result, *model_inputs]:
            reference = DataConverter.default.payload_converter.from_payload(payload)
            assert isinstance(reference, ExternalStorageReference)
            assert reference.driver_name == "aws.s3driver"
            assert payload.ByteSize() < 1024
        assert "x" * 1024 not in history.to_json()

    # A fresh client can decode the externally stored payloads for replay.
    async with connect_client(
        create_plugin, target_host=target_host, s3_endpoint=s3_endpoint
    ) as replay_client:
        await Replayer(
            workflows=[ExternalStorageAgent],
            data_converter=replay_client.data_converter,
            plugins=[create_plugin(replay_client.data_converter)],
        ).replay_workflow(history)
