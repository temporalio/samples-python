import asyncio
import uuid
from typing import Type

import pytest
from temporalio import workflow
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

import nexus_messaging.callerpattern.handler.worker
from nexus_messaging.callerpattern.caller.workflows import CallerWorkflow
from nexus_messaging.callerpattern.service import (
    GetLanguageInput,
    GetLanguagesInput,
    Language,
    SetLanguageInput,
)
from tests.helpers.nexus import create_nexus_endpoint, delete_nexus_endpoint

from nexus_messaging.callerpattern.service import NexusGreetingService

NEXUS_ENDPOINT = "nexus-messaging-nexus-endpoint"


@workflow.defn
class TestCallerWorkflow:
    """Test workflow that calls Nexus operations and makes assertions."""

    @workflow.run
    async def run(self, user_id: str) -> None:
        nexus_client = workflow.create_nexus_client(
            service=NexusGreetingService,
            endpoint=NEXUS_ENDPOINT,
        )

        supported_languages = await nexus_client.execute_operation(
            NexusGreetingService.get_languages,
            GetLanguagesInput(include_unsupported=False, user_id=user_id),
        )
        assert supported_languages.languages == [Language.CHINESE, Language.ENGLISH]

        initial_language = await nexus_client.execute_operation(
            NexusGreetingService.get_language,
            GetLanguageInput(user_id=user_id),
        )
        assert initial_language == Language.ENGLISH

        previous_language = await nexus_client.execute_operation(
            NexusGreetingService.set_language,
            SetLanguageInput(language=Language.CHINESE, user_id=user_id),
        )
        assert previous_language == Language.ENGLISH

        current_language = await nexus_client.execute_operation(
            NexusGreetingService.get_language,
            GetLanguageInput(user_id=user_id),
        )
        assert current_language == Language.CHINESE

        previous_language = await nexus_client.execute_operation(
            NexusGreetingService.set_language,
            SetLanguageInput(language=Language.ARABIC, user_id=user_id),
        )
        assert previous_language == Language.CHINESE

        current_language = await nexus_client.execute_operation(
            NexusGreetingService.get_language,
            GetLanguageInput(user_id=user_id),
        )
        assert current_language == Language.ARABIC


async def test_callerpattern(client: Client, env: WorkflowEnvironment):
    if env.supports_time_skipping:
        pytest.skip("Nexus tests don't work under the Java test server")

    await _run_caller_workflow(client, TestCallerWorkflow)


async def test_callerpattern_caller_workflow(client: Client, env: WorkflowEnvironment):
    """Runs the CallerWorkflow from the sample to ensure it executes without errors."""
    if env.supports_time_skipping:
        pytest.skip("Nexus tests don't work under the Java test server")

    await _run_caller_workflow(client, CallerWorkflow)


async def _run_caller_workflow(client: Client, wf: Type):
    create_response = await create_nexus_endpoint(
        name=NEXUS_ENDPOINT,
        task_queue=nexus_messaging.callerpattern.handler.worker.TASK_QUEUE,
        client=client,
    )
    try:
        handler_worker_task = asyncio.create_task(
            nexus_messaging.callerpattern.handler.worker.main(client)
        )
        try:
            async with Worker(
                client,
                task_queue="test-caller-task-queue",
                workflows=[wf],
            ):
                await client.execute_workflow(
                    wf.run,
                    arg="user-1",
                    id=str(uuid.uuid4()),
                    task_queue="test-caller-task-queue",
                )
        finally:
            nexus_messaging.callerpattern.handler.worker.interrupt_event.set()
            await handler_worker_task
            nexus_messaging.callerpattern.handler.worker.interrupt_event.clear()
    finally:
        await delete_nexus_endpoint(
            id=create_response.endpoint.id,
            version=create_response.endpoint.version,
            client=client,
        )
