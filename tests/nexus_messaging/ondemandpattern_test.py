import asyncio
import uuid
from typing import Type

import pytest
from temporalio import workflow
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

import nexus_messaging.ondemandpattern.handler.worker
from nexus_messaging.ondemandpattern.caller.workflows import CallerRemoteWorkflow
from nexus_messaging.ondemandpattern.service import (
    ApproveInput,
    GetLanguageInput,
    GetLanguagesInput,
    Language,
    NexusRemoteGreetingService,
    RunFromRemoteInput,
    SetLanguageInput,
)
from tests.helpers.nexus import create_nexus_endpoint, delete_nexus_endpoint

with workflow.unsafe.imports_passed_through():
    from nexus_messaging.ondemandpattern.service import NexusRemoteGreetingService


NEXUS_ENDPOINT = "nexus-messaging-nexus-endpoint"


@workflow.defn
class TestCallerRemoteWorkflow:
    """Test workflow that creates remote workflows and makes assertions."""

    @workflow.run
    async def run(self) -> None:
        nexus_client = workflow.create_nexus_client(
            service=NexusRemoteGreetingService,
            endpoint=NEXUS_ENDPOINT,
        )

        workflow_id = f"test-remote-{workflow.uuid4()}"

        # Start a remote workflow.
        handle = await nexus_client.start_operation(
            NexusRemoteGreetingService.run_from_remote,
            RunFromRemoteInput(user_id=workflow_id),
        )

        # Query for supported languages.
        languages_output = await nexus_client.execute_operation(
            NexusRemoteGreetingService.get_languages,
            GetLanguagesInput(include_unsupported=False, user_id=workflow_id),
        )
        assert languages_output.languages == [Language.CHINESE, Language.ENGLISH]

        # Check initial language.
        initial_language = await nexus_client.execute_operation(
            NexusRemoteGreetingService.get_language,
            GetLanguageInput(user_id=workflow_id),
        )
        assert initial_language == Language.ENGLISH

        # Set language.
        previous_language = await nexus_client.execute_operation(
            NexusRemoteGreetingService.set_language,
            SetLanguageInput(language=Language.ARABIC, user_id=workflow_id),
        )
        assert previous_language == Language.ENGLISH

        current_language = await nexus_client.execute_operation(
            NexusRemoteGreetingService.get_language,
            GetLanguageInput(user_id=workflow_id),
        )
        assert current_language == Language.ARABIC

        # Approve and wait for result.
        await nexus_client.execute_operation(
            NexusRemoteGreetingService.approve,
            ApproveInput(name="test", user_id=workflow_id),
        )

        result = await handle
        assert "\u0645\u0631\u062d\u0628\u0627" in result  # Arabic greeting


async def test_ondemandpattern(client: Client, env: WorkflowEnvironment):
    if env.supports_time_skipping:
        pytest.skip("Nexus tests don't work under the Java test server")

    await _run_caller_workflow(client, TestCallerRemoteWorkflow)


async def test_ondemandpattern_caller_workflow(
    client: Client, env: WorkflowEnvironment
):
    """Runs the CallerRemoteWorkflow from the sample to ensure it executes without errors."""
    if env.supports_time_skipping:
        pytest.skip("Nexus tests don't work under the Java test server")

    await _run_caller_workflow(client, CallerRemoteWorkflow)


async def _run_caller_workflow(client: Client, wf: Type):
    create_response = await create_nexus_endpoint(
        name=NEXUS_ENDPOINT,
        task_queue=nexus_messaging.ondemandpattern.handler.worker.TASK_QUEUE,
        client=client,
    )
    try:
        handler_worker_task = asyncio.create_task(
            nexus_messaging.ondemandpattern.handler.worker.main(client)
        )
        try:
            async with Worker(
                client,
                task_queue="test-caller-remote-task-queue",
                workflows=[wf],
            ):
                await client.execute_workflow(
                    wf.run,
                    id=str(uuid.uuid4()),
                    task_queue="test-caller-remote-task-queue",
                )
        finally:
            nexus_messaging.ondemandpattern.handler.worker.interrupt_event.set()
            await handler_worker_task
            nexus_messaging.ondemandpattern.handler.worker.interrupt_event.clear()
    finally:
        await delete_nexus_endpoint(
            id=create_response.endpoint.id,
            version=create_response.endpoint.version,
            client=client,
        )
