"""
Edge case tests for expense workflow and activities.
Tests parameter validation, retries, error scenarios, and boundary conditions.
"""

import uuid

import pytest
from temporalio import activity
from temporalio.client import Client, WorkflowFailureError
from temporalio.exceptions import ApplicationError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from expense.workflow import SampleExpenseWorkflow


class TestWorkflowEdgeCases:
    """Test edge cases in workflow behavior"""

    async def test_workflow_with_retryable_activity_failures(
        self, client: Client, env: WorkflowEnvironment
    ):
        """Test workflow behavior with retryable activity failures"""
        task_queue = f"test-retryable-failures-{uuid.uuid4()}"
        create_call_count = 0
        payment_call_count = 0

        @activity.defn(name="create_expense_activity")
        async def create_expense_retry(expense_id: str) -> None:
            nonlocal create_call_count
            create_call_count += 1
            if create_call_count == 1:
                # First call fails, but retryable
                raise Exception("Transient failure in create expense")
            return None  # Second call succeeds

        @activity.defn(name="wait_for_decision_activity")
        async def wait_for_decision_mock(expense_id: str) -> str:
            return "APPROVED"

        @activity.defn(name="payment_activity")
        async def payment_retry(expense_id: str) -> None:
            nonlocal payment_call_count
            payment_call_count += 1
            if payment_call_count == 1:
                # First call fails, but retryable
                raise Exception("Transient failure in payment")
            return None  # Second call succeeds

        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[SampleExpenseWorkflow],
            activities=[create_expense_retry, wait_for_decision_mock, payment_retry],
        ):
            result = await client.execute_workflow(
                SampleExpenseWorkflow.run,
                "test-expense-retryable",
                id=f"test-workflow-retryable-{uuid.uuid4()}",
                task_queue=task_queue,
            )

            # Should succeed after retries
            assert result == "COMPLETED"
            # Verify activities were retried
            assert create_call_count == 2
            assert payment_call_count == 2

    async def test_workflow_logging_behavior(
        self, client: Client, env: WorkflowEnvironment
    ):
        """Test that workflow logging works correctly"""
        task_queue = f"test-logging-{uuid.uuid4()}"
        logged_messages = []

        @activity.defn(name="create_expense_activity")
        async def create_expense_mock(expense_id: str) -> None:
            # Mock logging by capturing messages
            logged_messages.append(f"Creating expense: {expense_id}")
            return None

        @activity.defn(name="wait_for_decision_activity")
        async def wait_for_decision_mock(expense_id: str) -> str:
            logged_messages.append(f"Waiting for decision: {expense_id}")
            return "APPROVED"

        @activity.defn(name="payment_activity")
        async def payment_mock(expense_id: str) -> None:
            logged_messages.append(f"Processing payment: {expense_id}")
            return None

        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[SampleExpenseWorkflow],
            activities=[create_expense_mock, wait_for_decision_mock, payment_mock],
        ):
            result = await client.execute_workflow(
                SampleExpenseWorkflow.run,
                "test-expense-logging",
                id=f"test-workflow-logging-{uuid.uuid4()}",
                task_queue=task_queue,
            )

            assert result == "COMPLETED"
            # Verify logging occurred
            assert len(logged_messages) == 3
            assert "Creating expense: test-expense-logging" in logged_messages
            assert "Waiting for decision: test-expense-logging" in logged_messages
            assert "Processing payment: test-expense-logging" in logged_messages

    async def test_workflow_parameter_validation(
        self, client: Client, env: WorkflowEnvironment
    ):
        """Test workflow with various parameter validation scenarios"""
        task_queue = f"test-param-validation-{uuid.uuid4()}"

        @activity.defn(name="create_expense_activity")
        async def create_expense_validate(expense_id: str) -> None:
            if not expense_id or expense_id.strip() == "":
                raise ApplicationError(
                    "expense id is empty or whitespace", non_retryable=True
                )
            return None

        @activity.defn(name="wait_for_decision_activity")
        async def wait_for_decision_mock(expense_id: str) -> str:
            return "APPROVED"

        @activity.defn(name="payment_activity")
        async def payment_mock(expense_id: str) -> None:
            return None

        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[SampleExpenseWorkflow],
            activities=[create_expense_validate, wait_for_decision_mock, payment_mock],
        ):
            # Test with empty string
            with pytest.raises(WorkflowFailureError):
                await client.execute_workflow(
                    SampleExpenseWorkflow.run,
                    "",  # Empty expense ID
                    id=f"test-workflow-empty-id-{uuid.uuid4()}",
                    task_queue=task_queue,
                )

            # Test with whitespace-only string
            with pytest.raises(WorkflowFailureError):
                await client.execute_workflow(
                    SampleExpenseWorkflow.run,
                    "   ",  # Whitespace-only expense ID
                    id=f"test-workflow-whitespace-id-{uuid.uuid4()}",
                    task_queue=task_queue,
                )
