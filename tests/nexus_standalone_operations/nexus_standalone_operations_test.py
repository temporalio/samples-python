import asyncio
import os
import uuid
from datetime import timedelta

import pytest
from temporalio.client import Client, NexusOperationFailureError
from temporalio.service import RPCError
from temporalio.worker import Worker

from nexus_standalone_operations.handler import HelloWorkflow, MyNexusServiceHandler
from nexus_standalone_operations.service import (
    EchoInput,
    EchoOutput,
    HelloInput,
    HelloOutput,
    MyNexusService,
)
from nexus_standalone_operations.worker import TASK_QUEUE
from tests.helpers.nexus import create_nexus_endpoint, delete_nexus_endpoint


async def test_nexus_standalone_operations(client: Client):
    if not os.getenv("ENABLE_STANDALONE_NEXUS_TESTS"):
        pytest.skip(
            "Standalone Nexus operations not yet supported by default dev server. Set ENABLE_STANDALONE_NEXUS_TESTS=1 to enable."
        )

    endpoint_name = f"test-nexus-standalone-{uuid.uuid4()}"

    create_response = await create_nexus_endpoint(
        name=endpoint_name,
        task_queue=TASK_QUEUE,
        client=client,
    )
    try:
        async with Worker(
            client,
            task_queue=TASK_QUEUE,
            workflows=[HelloWorkflow],
            nexus_service_handlers=[MyNexusServiceHandler()],
        ):
            nexus_client = client.create_nexus_client(
                service=MyNexusService, endpoint=endpoint_name
            )

            # Test sync echo operation (with retry for endpoint propagation)
            echo_result = None
            for _ in range(30):
                try:
                    echo_result = await nexus_client.execute_operation(
                        MyNexusService.echo,
                        EchoInput(message="test-echo"),
                        id=str(uuid.uuid4()),
                        schedule_to_close_timeout=timedelta(seconds=10),
                    )
                    break
                except (RPCError, NexusOperationFailureError):
                    await asyncio.sleep(0.5)
            assert isinstance(echo_result, EchoOutput)
            assert echo_result.message == "test-echo"

            # Test async hello operation
            hello_result = await nexus_client.execute_operation(
                MyNexusService.hello,
                HelloInput(name="Test"),
                id=str(uuid.uuid4()),
                schedule_to_close_timeout=timedelta(seconds=10),
            )
            assert isinstance(hello_result, HelloOutput)
            assert hello_result.greeting == "Hello, Test!"

            # Test count operations
            count = await client.count_nexus_operations(f'Endpoint = "{endpoint_name}"')
            assert count.count >= 0
    finally:
        _ = await delete_nexus_endpoint(
            id=create_response.endpoint.id,
            version=create_response.endpoint.version,
            client=client,
        )
