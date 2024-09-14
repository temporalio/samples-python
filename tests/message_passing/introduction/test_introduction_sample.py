import uuid

import pytest
from temporalio.client import Client, WorkflowUpdateFailedError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from message_passing.introduction.starter import TASK_QUEUE
from message_passing.introduction.workflows import (
    GetLanguagesInput,
    GreetingWorkflow,
    Language,
    call_greeting_service,
)


async def test_queries(client: Client, env: WorkflowEnvironment):
    if env.supports_time_skipping:
        pytest.skip(
            "Java test server: https://github.com/temporalio/sdk-java/issues/1903"
        )
    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[GreetingWorkflow],
    ):
        wf_handle = await client.start_workflow(
            GreetingWorkflow.run,
            id=str(uuid.uuid4()),
            task_queue=TASK_QUEUE,
        )
        assert await wf_handle.query(GreetingWorkflow.get_language) == Language.ENGLISH
        assert await wf_handle.query(
            GreetingWorkflow.get_languages, GetLanguagesInput(include_unsupported=False)
        ) == [Language.CHINESE, Language.ENGLISH]
        assert await wf_handle.query(
            GreetingWorkflow.get_languages, GetLanguagesInput(include_unsupported=True)
        ) == [
            Language.ARABIC,
            Language.CHINESE,
            Language.ENGLISH,
            Language.FRENCH,
            Language.HINDI,
            Language.PORTUGUESE,
            Language.SPANISH,
        ]


async def test_set_language(client: Client, env: WorkflowEnvironment):
    if env.supports_time_skipping:
        pytest.skip(
            "Java test server: https://github.com/temporalio/sdk-java/issues/1903"
        )
    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[GreetingWorkflow],
    ):
        wf_handle = await client.start_workflow(
            GreetingWorkflow.run,
            id=str(uuid.uuid4()),
            task_queue=TASK_QUEUE,
        )
        assert await wf_handle.query(GreetingWorkflow.get_language) == Language.ENGLISH
        previous_language = await wf_handle.execute_update(
            GreetingWorkflow.set_language, Language.CHINESE
        )
        assert previous_language == Language.ENGLISH
        assert await wf_handle.query(GreetingWorkflow.get_language) == Language.CHINESE


async def test_set_invalid_language(client: Client, env: WorkflowEnvironment):
    if env.supports_time_skipping:
        pytest.skip(
            "Java test server: https://github.com/temporalio/sdk-java/issues/1903"
        )
    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[GreetingWorkflow],
    ):
        wf_handle = await client.start_workflow(
            GreetingWorkflow.run,
            id=str(uuid.uuid4()),
            task_queue=TASK_QUEUE,
        )
        assert await wf_handle.query(GreetingWorkflow.get_language) == Language.ENGLISH

        with pytest.raises(WorkflowUpdateFailedError):
            await wf_handle.execute_update(
                GreetingWorkflow.set_language, Language.ARABIC
            )


async def test_set_language_that_is_only_available_via_remote_service(
    client: Client, env: WorkflowEnvironment
):
    """
    Similar to test_set_invalid_language, but this time Arabic is available
    since we use the remote service.
    """
    if env.supports_time_skipping:
        pytest.skip(
            "Java test server: https://github.com/temporalio/sdk-java/issues/1903"
        )
    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[GreetingWorkflow],
        activities=[call_greeting_service],
    ):
        wf_handle = await client.start_workflow(
            GreetingWorkflow.run,
            id=str(uuid.uuid4()),
            task_queue=TASK_QUEUE,
        )
        assert await wf_handle.query(GreetingWorkflow.get_language) == Language.ENGLISH
        previous_language = await wf_handle.execute_update(
            GreetingWorkflow.set_language_using_activity,
            Language.ARABIC,
        )
        assert previous_language == Language.ENGLISH
        assert await wf_handle.query(GreetingWorkflow.get_language) == Language.ARABIC
