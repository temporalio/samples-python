import asyncio
import uuid

import pytest
from temporalio.client import Client, WorkflowUpdateFailedError
from temporalio.exceptions import ApplicationError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from reqrespupdate.activities import uppercase
from reqrespupdate.workflow import (
    BACKOFF_ERROR_TYPE,
    Request,
    UppercaseWorkflow,
    UppercaseWorkflowInput,
)


async def request_uppercase(handle, text: str, max_attempts: int = 10) -> str:
    """Request an uppercasing, retrying if the workflow is continuing as new.

    This is the same backoff the requester in this sample performs, bounded so
    that a workflow which never continues as new fails the test instead of
    retrying forever.
    """
    for _ in range(max_attempts):
        try:
            response = await handle.execute_update(
                UppercaseWorkflow.uppercase, Request(input=text)
            )
            return response.output
        except WorkflowUpdateFailedError as err:
            if (
                isinstance(err.cause, ApplicationError)
                and err.cause.type == BACKOFF_ERROR_TYPE
            ):
                await asyncio.sleep(0.1)
                continue
            raise
    raise AssertionError(
        f"Request for {text} still rejected after {max_attempts} attempts"
    )


async def test_uppercase(client: Client, env: WorkflowEnvironment):
    if env.supports_time_skipping:
        pytest.skip(
            "Java test server: https://github.com/temporalio/sdk-java/issues/1903"
        )
    task_queue = f"tq-{uuid.uuid4()}"
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[UppercaseWorkflow],
        activities=[uppercase],
    ):
        handle = await client.start_workflow(
            UppercaseWorkflow.run,
            UppercaseWorkflowInput(),
            id=f"reqrespupdate-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        try:
            for text in ["foo", "bar", "baz"]:
                assert await request_uppercase(handle, text) == text.upper()
        finally:
            await handle.terminate()


async def test_continues_as_new_without_losing_requests(
    client: Client, env: WorkflowEnvironment
):
    if env.supports_time_skipping:
        pytest.skip(
            "Java test server: https://github.com/temporalio/sdk-java/issues/1903"
        )
    task_queue = f"tq-{uuid.uuid4()}"
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[UppercaseWorkflow],
        activities=[uppercase],
    ):
        handle = await client.start_workflow(
            UppercaseWorkflow.run,
            # Low enough that the run continues as new several times over the
            # requests below.
            UppercaseWorkflowInput(requests_before_continue_as_new=2),
            id=f"reqrespupdate-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        try:
            # Whether any individual request is rejected depends on how the
            # continue-as-new interleaves with it, so we assert the contract the
            # requester actually relies on: every request eventually succeeds,
            # and the workflow does continue as new underneath.
            for i in range(6):
                assert await request_uppercase(handle, f"foo{i}") == f"FOO{i}"

            description = await handle.describe()
            assert description.run_id != handle.first_execution_run_id
        finally:
            await handle.terminate()
