import asyncio
import sys

import pytest
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment

import hello_nexus.caller.app
import hello_nexus.caller.workflows
import hello_nexus.handler.worker
from tests.hello_nexus.helpers import create_nexus_endpoint, delete_nexus_endpoint


async def test_nexus_service_basic(client: Client, env: WorkflowEnvironment):
    if env.supports_time_skipping:
        pytest.skip("Nexus tests don't work under the Java test server")

    if sys.version_info[:2] < (3, 10):
        pytest.skip("Sample is written for Python >= 3.10")

    create_response = await create_nexus_endpoint(
        name=hello_nexus.caller.workflows.NEXUS_ENDPOINT,
        task_queue=hello_nexus.handler.worker.TASK_QUEUE,
        client=client,
    )
    try:
        handler_worker_task = asyncio.create_task(
            hello_nexus.handler.worker.main(
                client,
            )
        )
        await asyncio.sleep(1)
        results = await hello_nexus.caller.app.execute_caller_workflow(
            client,
        )
        hello_nexus.handler.worker.interrupt_event.set()
        await handler_worker_task
        hello_nexus.handler.worker.interrupt_event.clear()
        assert [r.message for r in results] == [
            "Hello world from sync operation!",
            "Hello world from workflow run operation!",
        ]
    finally:
        await delete_nexus_endpoint(
            id=create_response.endpoint.id,
            version=create_response.endpoint.version,
            client=client,
        )
