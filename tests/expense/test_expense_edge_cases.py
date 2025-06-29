"""
Edge case tests for expense workflow and activities.
Tests parameter validation, retries, error scenarios, and boundary conditions.
"""

import asyncio
import uuid

import pytest
from temporalio import activity
from temporalio.client import Client, WorkflowFailureError
from temporalio.exceptions import ApplicationError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from expense.workflow import SampleExpenseWorkflow


class MockExpenseUI:
    """Mock UI that simulates the expense approval system"""

    def __init__(self, client: Client):
        self.client = client
        self.workflow_map: dict[str, str] = {}
        self.scheduled_decisions: dict[str, str] = {}

    def register_workflow(self, expense_id: str, workflow_id: str):
        """Register a workflow for an expense (simulates UI registration)"""
        self.workflow_map[expense_id] = workflow_id

    def schedule_decision(self, expense_id: str, decision: str, delay: float = 0.1):
        """Schedule a decision to be made after a delay (simulates human decision)"""
        self.scheduled_decisions[expense_id] = decision

        async def send_decision():
            await asyncio.sleep(delay)
            if expense_id in self.workflow_map:
                workflow_id = self.workflow_map[expense_id]
                handle = self.client.get_workflow_handle(workflow_id)
                await handle.signal("expense_decision_signal", decision)

        asyncio.create_task(send_decision())

    def create_register_activity(self):
        """Create a register activity that works with this mock UI"""

        @activity.defn(name="register_for_decision_activity")
        async def register_decision_activity(expense_id: str) -> None:
            # Simulate automatic decision if one was scheduled
            if expense_id in self.scheduled_decisions:
                # Decision will be sent by the scheduled task
                pass
            return None

        return register_decision_activity


class TestWorkflowEdgeCases:
    """Test edge cases in workflow behavior"""

    async def test_workflow_with_retryable_activity_failures(
        self, client: Client, env: WorkflowEnvironment
    ):
        """Test workflow behavior with retryable activity failures"""
        task_queue = f"test-retryable-failures-{uuid.uuid4()}"
        workflow_id = f"test-workflow-retryable-{uuid.uuid4()}"
        expense_id = "test-expense-retryable"
        create_call_count = 0
        payment_call_count = 0

        # Set up mock UI with APPROVED decision
        mock_ui = MockExpenseUI(client)
        mock_ui.register_workflow(expense_id, workflow_id)
        mock_ui.schedule_decision(expense_id, "APPROVED")

        @activity.defn(name="create_expense_activity")
        async def create_expense_retry(expense_id: str) -> None:
            nonlocal create_call_count
            create_call_count += 1
            if create_call_count == 1:
                # First call fails, but retryable
                raise Exception("Transient failure in create expense")
            return None  # Second call succeeds

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
            activities=[
                create_expense_retry,
                mock_ui.create_register_activity(),
                payment_retry,
            ],
        ):
            result = await client.execute_workflow(
                SampleExpenseWorkflow.run,
                expense_id,
                id=workflow_id,
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
        workflow_id = f"test-workflow-logging-{uuid.uuid4()}"
        expense_id = "test-expense-logging"
        logged_messages = []

        # Set up mock UI with APPROVED decision
        mock_ui = MockExpenseUI(client)
        mock_ui.register_workflow(expense_id, workflow_id)
        mock_ui.schedule_decision(expense_id, "APPROVED")

        @activity.defn(name="create_expense_activity")
        async def create_expense_mock(expense_id: str) -> None:
            # Mock logging by capturing messages
            logged_messages.append(f"Creating expense: {expense_id}")
            return None

        @activity.defn(name="payment_activity")
        async def payment_mock(expense_id: str) -> None:
            logged_messages.append(f"Processing payment: {expense_id}")
            return None

        # Create logging register activity
        def create_logging_register_activity():
            @activity.defn(name="register_for_decision_activity")
            async def register_decision_logging(expense_id: str) -> None:
                logged_messages.append(f"Waiting for decision: {expense_id}")
                # Simulate automatic decision if one was scheduled
                if expense_id in mock_ui.scheduled_decisions:
                    # Decision will be sent by the scheduled task
                    pass
                return None

            return register_decision_logging

        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[SampleExpenseWorkflow],
            activities=[
                create_expense_mock,
                create_logging_register_activity(),
                payment_mock,
            ],
        ):
            result = await client.execute_workflow(
                SampleExpenseWorkflow.run,
                expense_id,
                id=workflow_id,
                task_queue=task_queue,
            )

            assert result == "COMPLETED"
            # Verify logging occurred
            assert len(logged_messages) == 3
            assert f"Creating expense: {expense_id}" in logged_messages
            assert f"Waiting for decision: {expense_id}" in logged_messages
            assert f"Processing payment: {expense_id}" in logged_messages

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

        @activity.defn(name="register_for_decision_activity")
        async def wait_for_decision_mock(expense_id: str) -> None:
            return None

        @activity.defn(name="payment_activity")
        async def payment_mock(expense_id: str) -> None:
            return None

        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[SampleExpenseWorkflow],
            activities=[create_expense_validate, wait_for_decision_mock, payment_mock],
        ):
            # Test with empty string - this should fail at create_expense_activity
            with pytest.raises(WorkflowFailureError):
                await client.execute_workflow(
                    SampleExpenseWorkflow.run,
                    "",  # Empty expense ID
                    id=f"test-workflow-empty-id-{uuid.uuid4()}",
                    task_queue=task_queue,
                )

            # Test with whitespace-only string - this should fail at create_expense_activity
            with pytest.raises(WorkflowFailureError):
                await client.execute_workflow(
                    SampleExpenseWorkflow.run,
                    "   ",  # Whitespace-only expense ID
                    id=f"test-workflow-whitespace-id-{uuid.uuid4()}",
                    task_queue=task_queue,
                )
