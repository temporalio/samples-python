import asyncio
import uuid
from typing import Type

import pytest
from temporalio import workflow
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

import nexus_sync_operations.handler.service_handler
import nexus_sync_operations.handler.worker
from message_passing.introduction import Language
from message_passing.introduction.workflows import GetLanguagesInput, SetLanguageInput
from nexus_sync_operations.caller.workflows import CallerWorkflow
from tests.helpers.nexus import create_nexus_endpoint, delete_nexus_endpoint

with workflow.unsafe.imports_passed_through():
    from nexus_sync_operations.service import GreetingService


NEXUS_ENDPOINT = "nexus-sync-operations-nexus-endpoint"


@workflow.defn
class TestCallerWorkflow:
    """Test workflow that calls Nexus operations and makes assertions."""

    @workflow.run
    async def run(self) -> None:
        nexus_client = workflow.create_nexus_client(
            service=GreetingService,
            endpoint=NEXUS_ENDPOINT,
        )

        supported_languages = await nexus_client.execute_operation(
            GreetingService.get_languages, GetLanguagesInput(include_unsupported=False)
        )
        assert supported_languages == [Language.CHINESE, Language.ENGLISH]

        initial_language = await nexus_client.execute_operation(
            GreetingService.get_language, None
        )
        assert initial_language == Language.ENGLISH

        previous_language = await nexus_client.execute_operation(
            GreetingService.set_language,
            SetLanguageInput(language=Language.CHINESE),
        )
        assert previous_language == Language.ENGLISH

        current_language = await nexus_client.execute_operation(
            GreetingService.get_language, None
        )
        assert current_language == Language.CHINESE

        previous_language = await nexus_client.execute_operation(
            GreetingService.set_language,
            SetLanguageInput(language=Language.ARABIC),
        )
        assert previous_language == Language.CHINESE

        current_language = await nexus_client.execute_operation(
            GreetingService.get_language, None
        )
        assert current_language == Language.ARABIC


async def test_nexus_sync_operations(client: Client, env: WorkflowEnvironment):
    if env.supports_time_skipping:
        pytest.skip("Nexus tests don't work under the Java test server")

    await _run_caller_workflow(client, TestCallerWorkflow)


async def test_nexus_sync_operations_caller_workflow(
    client: Client, env: WorkflowEnvironment
):
    """
    Runs the CallerWorkflow from the sample to ensure it executes without errors.
    """
    if env.supports_time_skipping:
        pytest.skip("Nexus tests don't work under the Java test server")

    await _run_caller_workflow(client, CallerWorkflow)


async def _run_caller_workflow(client: Client, workflow: Type):
    create_response = await create_nexus_endpoint(
        name=NEXUS_ENDPOINT,
        task_queue=nexus_sync_operations.handler.worker.TASK_QUEUE,
        client=client,
    )
    try:
        await (
            nexus_sync_operations.handler.service_handler.GreetingServiceHandler.start(
                client, nexus_sync_operations.handler.worker.TASK_QUEUE
            )
        )
        handler_worker_task = asyncio.create_task(
            nexus_sync_operations.handler.worker.main(client)
        )
        try:
            async with Worker(
                client,
                task_queue="test-caller-task-queue",
                workflows=[workflow],
            ):
                await client.execute_workflow(
                    workflow.run,
                    id=str(uuid.uuid4()),
                    task_queue="test-caller-task-queue",
                )
        finally:
            nexus_sync_operations.handler.worker.interrupt_event.set()
            await handler_worker_task
            nexus_sync_operations.handler.worker.interrupt_event.clear()
            try:
                await client.get_workflow_handle(
                    nexus_sync_operations.handler.service_handler.GreetingServiceHandler.LONG_RUNNING_WORKFLOW_ID
                ).terminate()
            except Exception:
                pass
    finally:
        await delete_nexus_endpoint(
            id=create_response.endpoint.id,
            version=create_response.endpoint.version,
            client=client,
        )
