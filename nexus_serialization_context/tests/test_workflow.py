import asyncio
from contextlib import AsyncExitStack
from uuid import uuid4

from google.protobuf.duration_pb2 import Duration
from temporalio.api.workflowservice.v1 import RegisterNamespaceRequest
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from config import (
    caller_data_converter,
    compressed_encrypted_data_converter,
    encrypted_data_converter,
)
from handler import AsyncEchoHandler, SyncEchoHandler
from service import (
    CALLER_NAMESPACE,
    COMPRESSED_ENCRYPTED_NAMESPACE,
    ENCRYPTED_NAMESPACE,
    ENDPOINTS,
    EndpointResults,
)
from workflows import CallerWorkflow, EchoWorkflow


async def test_sync_and_async_operations_through_all_four_endpoints():
    async with await WorkflowEnvironment.start_local(
        dev_server_download_version="v1.9.3-nexus-serialization-context"
    ) as env:
        async with AsyncExitStack() as stack:
            clients = {}
            for namespace, converter, endpoints in [
                (CALLER_NAMESPACE, caller_data_converter(), ()),
                (
                    COMPRESSED_ENCRYPTED_NAMESPACE,
                    compressed_encrypted_data_converter(),
                    ENDPOINTS[:2],
                ),
                (ENCRYPTED_NAMESPACE, encrypted_data_converter(), ENDPOINTS[2:]),
            ]:
                await env.client.workflow_service.register_namespace(
                    RegisterNamespaceRequest(
                        namespace=namespace,
                        workflow_execution_retention_period=Duration(seconds=86400),
                    )
                )
                client = await Client.connect(
                    env.client.service_client.config.target_host,
                    namespace=namespace,
                    data_converter=converter,
                )
                clients[namespace] = client
                await stack.enter_async_context(
                    Worker(
                        client,
                        task_queue=namespace,
                        workflows=[EchoWorkflow] if endpoints else [CallerWorkflow],
                        nexus_service_handlers=(
                            [SyncEchoHandler(), AsyncEchoHandler()] if endpoints else []
                        ),
                    )
                )
                for endpoint in endpoints:
                    await WorkflowEnvironment.from_client(client).create_nexus_endpoint(
                        endpoint, namespace
                    )
                if namespace == CALLER_NAMESPACE:
                    caller = client

            handle = await caller.start_workflow(
                CallerWorkflow.run,
                "Hello from Nexus",
                id=f"nexus-serialization-{uuid4()}",
                task_queue=CALLER_NAMESPACE,
            )
            results = await asyncio.wait_for(handle.result(), timeout=45)
            assert results == {
                endpoint: EndpointResults("Hello from Nexus", "Hello from Nexus")
                for endpoint in ENDPOINTS
            }

            history = await handle.fetch_history()
            scheduled = [
                event.nexus_operation_scheduled_event_attributes
                for event in history.events
                if event.HasField("nexus_operation_scheduled_event_attributes")
            ]
            assert sorted(
                (op.endpoint, op.service, op.operation) for op in scheduled
            ) == sorted(
                (endpoint, service, operation)
                for endpoint in ENDPOINTS
                for service, operation in [
                    ("SyncEchoService", "echo"),
                    ("AsyncEchoService", "echoAsync"),
                ]
            )
            for operation in scheduled:
                if operation.operation != "echoAsync":
                    continue
                compressed = operation.endpoint in ENDPOINTS[:2]
                namespace = (
                    COMPRESSED_ENCRYPTED_NAMESPACE
                    if compressed
                    else ENCRYPTED_NAMESPACE
                )
                backing = clients[namespace].get_workflow_handle(
                    f"nexus-echo-{operation.request_id}"
                )
                backing_history = await backing.fetch_history()
                started = backing_history.events[
                    0
                ].workflow_execution_started_event_attributes
                completed = backing_history.events[
                    -1
                ].workflow_execution_completed_event_attributes
                context = started.propagated_nexus_serialization_context
                assert (context.endpoint, context.service, context.operation) == (
                    operation.endpoint,
                    "AsyncEchoService",
                    "echoAsync",
                )
                assert started.input.payloads[0].metadata == {
                    "encoding": b"binary/nexus-aes-gcm",
                    "encryption-key-id": (
                        b"compressed-encrypted-1" if compressed else b"encrypted-1"
                    ),
                }
                assert completed.result.payloads[0].metadata == {
                    "encoding": b"binary/nexus-aes-gcm",
                    "encryption-key-id": operation.endpoint.removeprefix(
                        "nexus-serialization-"
                    ).encode(),
                    "nexus-endpoint-name": operation.endpoint.encode(),
                }
