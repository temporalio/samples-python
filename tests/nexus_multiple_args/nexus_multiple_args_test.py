import asyncio
import sys

import pytest
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment

import nexus_multiple_args.caller.app
import nexus_multiple_args.caller.workflows
import nexus_multiple_args.handler.worker
from tests.helpers.nexus import create_nexus_endpoint, delete_nexus_endpoint


async def test_nexus_multiple_args(client: Client, env: WorkflowEnvironment):
    if env.supports_time_skipping:
        pytest.skip("Nexus tests don't work under the Java test server")

    if sys.version_info[:2] < (3, 10):
        pytest.skip("Sample is written for Python >= 3.10")

    create_response = await create_nexus_endpoint(
        name=nexus_multiple_args.caller.workflows.NEXUS_ENDPOINT,
        task_queue=nexus_multiple_args.handler.worker.TASK_QUEUE,
        client=client,
    )
    try:
        handler_worker_task = asyncio.create_task(
            nexus_multiple_args.handler.worker.main(
                client,
            )
        )
        await asyncio.sleep(1)
        results = await nexus_multiple_args.caller.app.execute_caller_workflow(
            client,
        )
        nexus_multiple_args.handler.worker.interrupt_event.set()
        await handler_worker_task
        nexus_multiple_args.handler.worker.interrupt_event.clear()

        # Verify the expected output messages
        assert results == (
            "Hello Nexus 👋",
            "¡Hola! Nexus 👋",
        )
    finally:
        await delete_nexus_endpoint(
            id=create_response.endpoint.id,
            version=create_response.endpoint.version,
            client=client,
        )
