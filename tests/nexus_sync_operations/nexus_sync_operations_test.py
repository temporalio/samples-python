import asyncio
import sys

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

    if sys.version_info[:2] < (3, 10):
        pytest.skip("Sample is written for Python >= 3.10")

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
        # Give worker time to start the long-running workflow
        await asyncio.sleep(1)

        # Execute the caller workflow which will test all the Nexus operations
        await nexus_sync_operations.caller.app.execute_caller_workflow(
            client,
        )

        # Clean up the handler worker
        nexus_sync_operations.handler.worker.interrupt_event.set()
        await handler_worker_task
        nexus_sync_operations.handler.worker.interrupt_event.clear()

        # The test passes if the caller workflow completes successfully
        # The caller workflow verifies that:
        # - get_languages returns supported languages
        # - set_language updates the language and returns the previous one
        # - get_language returns the current language
        # - set_language_using_activity updates the language using an activity
        # - approve sends the signal successfully
    finally:
        await delete_nexus_endpoint(
            id=create_response.endpoint.id,
            version=create_response.endpoint.version,
            client=client,
        )
