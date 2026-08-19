import uuid
from datetime import timedelta

import pytest
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from nexus_standalone_activity.activity import create_greeting
from nexus_standalone_activity.handler import GreetingServiceHandler
from nexus_standalone_activity.service import (
    GreetingInput,
    GreetingOutput,
    GreetingService,
)
from nexus_standalone_activity.worker import TASK_QUEUE
from tests.helpers.nexus import create_nexus_endpoint, delete_nexus_endpoint


async def test_nexus_operation_backed_by_standalone_activity(
    client: Client, env: WorkflowEnvironment
) -> None:
    if env.supports_time_skipping:
        pytest.skip("Time-skipping server does not support standalone Nexus operations")

    endpoint_name = f"test-nexus-standalone-activity-{uuid.uuid4()}"
    create_response = await create_nexus_endpoint(
        name=endpoint_name,
        task_queue=TASK_QUEUE,
        client=client,
    )
    try:
        async with Worker(
            client,
            task_queue=TASK_QUEUE,
            activities=[create_greeting],
            nexus_service_handlers=[GreetingServiceHandler()],
        ):
            nexus_client = client.create_nexus_client(
                service=GreetingService,
                endpoint=endpoint_name,
            )
            result = await nexus_client.execute_operation(
                GreetingService.greet,
                GreetingInput(name="Test"),
                id=str(uuid.uuid4()),
                schedule_to_close_timeout=timedelta(seconds=10),
            )

            assert isinstance(result, GreetingOutput)
            assert result.message == "Hello, Test!"
    finally:
        _ = await delete_nexus_endpoint(
            id=create_response.endpoint.id,
            version=create_response.endpoint.version,
            client=client,
        )
