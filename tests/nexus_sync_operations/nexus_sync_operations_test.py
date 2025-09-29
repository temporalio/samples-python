import asyncio

import pytest
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment

import nexus_sync_operations.caller.app
import nexus_sync_operations.caller.workflows
import nexus_sync_operations.handler.worker
from tests.helpers.nexus import create_nexus_endpoint, delete_nexus_endpoint


async def test_nexus_sync_operations(client: Client, env: WorkflowEnvironment):
    if env.supports_time_skipping:
        pytest.skip("Nexus tests don't work under the Java test server")

    create_response = await create_nexus_endpoint(
        name=nexus_sync_operations.caller.workflows.NEXUS_ENDPOINT,
        task_queue=nexus_sync_operations.handler.worker.TASK_QUEUE,
        client=client,
    )
    try:
        handler_worker_task = asyncio.create_task(
            nexus_sync_operations.handler.worker.main(
                client,
            )
        )
        await nexus_sync_operations.caller.app.execute_caller_workflow(
            client,
        )
        nexus_sync_operations.handler.worker.interrupt_event.set()
        await handler_worker_task
        nexus_sync_operations.handler.worker.interrupt_event.clear()
    finally:
        await delete_nexus_endpoint(
            id=create_response.endpoint.id,
            version=create_response.endpoint.version,
            client=client,
        )
