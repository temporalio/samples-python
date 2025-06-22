import uuid

import pytest
from temporalio import activity
from temporalio.client import Client, WorkflowFailureError
from temporalio.exceptions import ApplicationError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from expense.workflow import SampleExpenseWorkflow


async def test_workflow_with_mock_activities(client: Client, env: WorkflowEnvironment):
    """Test workflow with mocked activities"""
    task_queue = f"test-expense-{uuid.uuid4()}"

    # Mock the activities to return expected values
    @activity.defn(name="create_expense_activity")
    async def create_expense_mock(expense_id: str) -> None:
        # Mock succeeds by returning None
        return None

    @activity.defn(name="wait_for_decision_activity")
    async def wait_for_decision_mock(expense_id: str) -> str:
        # Mock returns APPROVED
        return "APPROVED"

    @activity.defn(name="payment_activity")
    async def payment_mock(expense_id: str) -> None:
        # Mock succeeds by returning None
        return None

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[SampleExpenseWorkflow],
        activities=[create_expense_mock, wait_for_decision_mock, payment_mock],
    ):
        # Execute workflow
        result = await client.execute_workflow(
            SampleExpenseWorkflow.run,
            "test-expense-id",
            id=f"test-expense-workflow-{uuid.uuid4()}",
            task_queue=task_queue,
        )

        # Verify result
        assert result == "COMPLETED"


async def test_workflow_rejected_expense(client: Client, env: WorkflowEnvironment):
    """Test workflow when expense is rejected"""
    task_queue = f"test-expense-rejected-{uuid.uuid4()}"

    # Mock the activities
    @activity.defn(name="create_expense_activity")
    async def create_expense_mock(expense_id: str) -> None:
        # Mock succeeds by returning None
        return None

    @activity.defn(name="wait_for_decision_activity")
    async def wait_for_decision_mock(expense_id: str) -> str:
        # Mock returns REJECTED
        return "REJECTED"

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[SampleExpenseWorkflow],
        activities=[create_expense_mock, wait_for_decision_mock],
    ):
        # Execute workflow
        result = await client.execute_workflow(
            SampleExpenseWorkflow.run,
            "test-expense-id",
            id=f"test-expense-rejected-workflow-{uuid.uuid4()}",
            task_queue=task_queue,
        )

        # Verify result is empty string when rejected
        assert result == ""


async def test_workflow_create_expense_failure(
    client: Client, env: WorkflowEnvironment
):
    """Test workflow when create expense activity fails"""
    task_queue = f"test-expense-failure-{uuid.uuid4()}"

    # Mock create_expense_activity to fail with non-retryable error
    @activity.defn(name="create_expense_activity")
    async def failing_create_expense(expense_id: str):
        raise ApplicationError("Failed to create expense", non_retryable=True)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[SampleExpenseWorkflow],
        activities=[failing_create_expense],
    ):
        # Execute workflow and expect it to fail
        with pytest.raises(WorkflowFailureError):
            await client.execute_workflow(
                SampleExpenseWorkflow.run,
                "test-expense-id",
                id=f"test-expense-failure-workflow-{uuid.uuid4()}",
                task_queue=task_queue,
            )
