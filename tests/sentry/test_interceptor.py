import unittest.mock
from collections import abc

import pytest
import sentry_sdk
import temporalio.activity
import temporalio.workflow
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import (
    SandboxedWorkflowRunner,
    SandboxRestrictions,
)

from sentry.activity import broken_activity, working_activity
from sentry.interceptor import SentryInterceptor
from sentry.workflow import SentryExampleWorkflow, SentryExampleWorkflowInput
from tests.sentry.fake_sentry_transport import FakeSentryTransport


@pytest.fixture
def transport() -> FakeSentryTransport:
    """Fixture to provide a fake transport for Sentry SDK."""
    return FakeSentryTransport()


@pytest.fixture(autouse=True)
def sentry_init(transport: FakeSentryTransport) -> None:
    """Initialize Sentry for testing."""
    sentry_sdk.init(
        # Pass __callable__ explicitly so SDK treats it as Callable[[Event], None]
        # it confuses it otherwise
        transport=transport.__callable__,
        integrations=[
            AsyncioIntegration(),
        ],
    )


@pytest.fixture
async def worker(client: Client) -> abc.AsyncIterator[Worker]:
    """Fixture to provide a worker for testing."""
    async with Worker(
        client,
        task_queue="sentry-task-queue",
        workflows=[SentryExampleWorkflow],
        activities=[broken_activity, working_activity],
        interceptors=[SentryInterceptor()],
        workflow_runner=SandboxedWorkflowRunner(
            restrictions=SandboxRestrictions.default.with_passthrough_modules(
                "sentry_sdk"
            )
        ),
    ) as worker:
        yield worker


async def test_sentry_interceptor_reports_no_errors_when_workflow_succeeds(
    client: Client, worker: Worker, transport: FakeSentryTransport
) -> None:
    """Test that Sentry interceptor reports no errors when workflow succeeds."""
    # WHEN
    try:
        await client.execute_workflow(
            SentryExampleWorkflow.run,
            SentryExampleWorkflowInput(option="working"),
            id="sentry-workflow-id",
            task_queue=worker.task_queue,
        )
    except Exception:
        pytest.fail("Workflow should not raise an exception")

    # THEN
    assert len(transport.events) == 0, "No events should be captured"


async def test_sentry_interceptor_captures_errors(
    client: Client, worker: Worker, transport: FakeSentryTransport
) -> None:
    """Test that errors are captured with correct Sentry metadata."""
    # WHEN
    try:
        await client.execute_workflow(
            SentryExampleWorkflow.run,
            SentryExampleWorkflowInput(option="broken"),
            id="sentry-workflow-id",
            task_queue=worker.task_queue,
        )
        pytest.fail("Workflow should raise an exception")
    except Exception:
        pass

    # THEN
    # there should be two events: one for the failed activity and one for the failed workflow
    assert len(transport.events) == 2, "Two events should be captured"

    # Check the first event - should be the activity exception
    # --------------------------------------------------------
    event = transport.events[0]

    # Check exception was captured
    assert event["exception"]["values"][0]["type"] == "Exception"
    assert event["exception"]["values"][0]["value"] == "Activity failed!"

    # Check useful metadata were were captured as tags
    assert event["tags"] == {
        "temporal.execution_type": "activity",
        "module": "sentry.activity.broken_activity",
        "temporal.workflow.type": "SentryExampleWorkflow",
        "temporal.workflow.id": "sentry-workflow-id",
        "temporal.activity.id": "1",
        "temporal.activity.type": "broken_activity",
        "temporal.activity.task_queue": "sentry-task-queue",
        "temporal.workflow.namespace": "default",
        "temporal.workflow.run_id": unittest.mock.ANY,
    }

    # Check activity input was captured as context
    assert event["contexts"]["temporal.activity.input"] == {
        "message": "Hello, Temporal!",
    }

    # Check activity info was captured as context
    activity_info = temporalio.activity.Info(
        **event["contexts"]["temporal.activity.info"]  # type: ignore
    )
    assert activity_info.activity_type == "broken_activity"

    # Check the second event - should be the workflow exception
    # ---------------------------------------------------------
    event = transport.events[1]

    # Check exception was captured
    assert event["exception"]["values"][0]["type"] == "ApplicationError"
    assert event["exception"]["values"][0]["value"] == "Activity failed!"

    # Check useful metadata were were captured as tags
    assert event["tags"] == {
        "temporal.execution_type": "workflow",
        "module": "sentry.workflow.SentryExampleWorkflow.run",
        "temporal.workflow.type": "SentryExampleWorkflow",
        "temporal.workflow.id": "sentry-workflow-id",
        "temporal.workflow.task_queue": "sentry-task-queue",
        "temporal.workflow.namespace": "default",
        "temporal.workflow.run_id": unittest.mock.ANY,
    }

    # Check workflow input was captured as context
    assert event["contexts"]["temporal.workflow.input"] == {
        "option": "broken",
    }

    # Check workflow info was captured as context
    workflow_info = temporalio.workflow.Info(
        **event["contexts"]["temporal.workflow.info"]  # type: ignore
    )
    assert workflow_info.workflow_type == "SentryExampleWorkflow"
