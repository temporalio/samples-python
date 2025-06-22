"""
Tests for the SampleExpenseWorkflow orchestration logic.
Focuses on workflow behavior, decision paths, and error propagation.
"""

import uuid
from datetime import timedelta

import pytest
from temporalio import activity
from temporalio.client import Client, WorkflowFailureError
from temporalio.exceptions import ApplicationError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from expense.workflow import SampleExpenseWorkflow


class TestWorkflowPaths:
    """Test main workflow execution paths"""

    async def test_workflow_approved_complete_flow(
        self, client: Client, env: WorkflowEnvironment
    ):
        """Test complete approved expense workflow - Happy Path"""
        task_queue = f"test-expense-approved-{uuid.uuid4()}"

        @activity.defn(name="create_expense_activity")
        async def create_expense_mock(expense_id: str) -> None:
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
            activities=[create_expense_mock, wait_for_decision_mock, payment_mock],
        ):
            result = await client.execute_workflow(
                SampleExpenseWorkflow.run,
                "test-expense-approved",
                id=f"test-workflow-approved-{uuid.uuid4()}",
                task_queue=task_queue,
            )

            assert result == "COMPLETED"

    async def test_workflow_rejected_flow(
        self, client: Client, env: WorkflowEnvironment
    ):
        """Test rejected expense workflow - Returns empty string"""
        task_queue = f"test-expense-rejected-{uuid.uuid4()}"

        @activity.defn(name="create_expense_activity")
        async def create_expense_mock(expense_id: str) -> None:
            return None

        @activity.defn(name="wait_for_decision_activity")
        async def wait_for_decision_mock(expense_id: str) -> str:
            return "REJECTED"

        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[SampleExpenseWorkflow],
            activities=[create_expense_mock, wait_for_decision_mock],
        ):
            result = await client.execute_workflow(
                SampleExpenseWorkflow.run,
                "test-expense-rejected",
                id=f"test-workflow-rejected-{uuid.uuid4()}",
                task_queue=task_queue,
            )

            assert result == ""

    async def test_workflow_other_decision_treated_as_rejected(
        self, client: Client, env: WorkflowEnvironment
    ):
        """Test that non-APPROVED decisions are treated as rejection"""
        task_queue = f"test-expense-other-{uuid.uuid4()}"

        @activity.defn(name="create_expense_activity")
        async def create_expense_mock(expense_id: str) -> None:
            return None

        @activity.defn(name="wait_for_decision_activity")
        async def wait_for_decision_mock(expense_id: str) -> str:
            return "PENDING"  # Any non-APPROVED value

        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[SampleExpenseWorkflow],
            activities=[create_expense_mock, wait_for_decision_mock],
        ):
            result = await client.execute_workflow(
                SampleExpenseWorkflow.run,
                "test-expense-other",
                id=f"test-workflow-other-{uuid.uuid4()}",
                task_queue=task_queue,
            )

            assert result == ""

    async def test_workflow_decision_values(
        self, client: Client, env: WorkflowEnvironment
    ):
        """Test that workflow returns correct values for different decisions"""
        task_queue = f"test-decisions-{uuid.uuid4()}"

        # Test cases: any non-"APPROVED" decision should return empty string
        test_cases = [
            ("APPROVED", "COMPLETED"),
            ("REJECTED", ""),
            ("DENIED", ""),
            ("PENDING", ""),
            ("CANCELLED", ""),
            ("UNKNOWN", ""),
        ]

        for decision, expected_result in test_cases:

            @activity.defn(name="create_expense_activity")
            async def create_expense_mock(expense_id: str) -> None:
                return None

            @activity.defn(name="wait_for_decision_activity")
            async def wait_for_decision_mock(expense_id: str) -> str:
                return decision

            @activity.defn(name="payment_activity")
            async def payment_mock(expense_id: str) -> None:
                return None

            async with Worker(
                client,
                task_queue=task_queue,
                workflows=[SampleExpenseWorkflow],
                activities=[create_expense_mock, wait_for_decision_mock, payment_mock],
            ):
                result = await client.execute_workflow(
                    SampleExpenseWorkflow.run,
                    f"test-expense-{decision.lower()}",
                    id=f"test-workflow-decision-{decision.lower()}-{uuid.uuid4()}",
                    task_queue=task_queue,
                )

                assert (
                    result == expected_result
                ), f"Decision '{decision}' should return '{expected_result}', got '{result}'"


class TestWorkflowFailures:
    """Test workflow behavior when activities fail"""

    async def test_workflow_create_expense_failure(
        self, client: Client, env: WorkflowEnvironment
    ):
        """Test workflow when create expense activity fails"""
        task_queue = f"test-create-failure-{uuid.uuid4()}"

        @activity.defn(name="create_expense_activity")
        async def failing_create_expense(expense_id: str):
            raise ApplicationError("Failed to create expense", non_retryable=True)

        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[SampleExpenseWorkflow],
            activities=[failing_create_expense],
        ):
            with pytest.raises(WorkflowFailureError):
                await client.execute_workflow(
                    SampleExpenseWorkflow.run,
                    "test-expense-create-fail",
                    id=f"test-workflow-create-fail-{uuid.uuid4()}",
                    task_queue=task_queue,
                )

    async def test_workflow_wait_decision_failure(
        self, client: Client, env: WorkflowEnvironment
    ):
        """Test workflow when wait for decision activity fails"""
        task_queue = f"test-wait-failure-{uuid.uuid4()}"

        @activity.defn(name="create_expense_activity")
        async def create_expense_mock(expense_id: str) -> None:
            return None

        @activity.defn(name="wait_for_decision_activity")
        async def failing_wait_decision(expense_id: str) -> str:
            raise ApplicationError("Failed to register callback", non_retryable=True)

        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[SampleExpenseWorkflow],
            activities=[create_expense_mock, failing_wait_decision],
        ):
            with pytest.raises(WorkflowFailureError):
                await client.execute_workflow(
                    SampleExpenseWorkflow.run,
                    "test-expense-wait-fail",
                    id=f"test-workflow-wait-fail-{uuid.uuid4()}",
                    task_queue=task_queue,
                )

    async def test_workflow_payment_failure(
        self, client: Client, env: WorkflowEnvironment
    ):
        """Test workflow when payment activity fails after approval"""
        task_queue = f"test-payment-failure-{uuid.uuid4()}"

        @activity.defn(name="create_expense_activity")
        async def create_expense_mock(expense_id: str) -> None:
            return None

        @activity.defn(name="wait_for_decision_activity")
        async def wait_for_decision_mock(expense_id: str) -> str:
            return "APPROVED"

        @activity.defn(name="payment_activity")
        async def failing_payment(expense_id: str):
            raise ApplicationError("Payment processing failed", non_retryable=True)

        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[SampleExpenseWorkflow],
            activities=[create_expense_mock, wait_for_decision_mock, failing_payment],
        ):
            with pytest.raises(WorkflowFailureError):
                await client.execute_workflow(
                    SampleExpenseWorkflow.run,
                    "test-expense-payment-fail",
                    id=f"test-workflow-payment-fail-{uuid.uuid4()}",
                    task_queue=task_queue,
                )


class TestWorkflowConfiguration:
    """Test workflow timeout and configuration behavior"""

    async def test_workflow_timeout_configuration(
        self, client: Client, env: WorkflowEnvironment
    ):
        """Test that workflow uses correct timeout configurations"""
        task_queue = f"test-timeouts-{uuid.uuid4()}"
        timeout_calls = []

        @activity.defn(name="create_expense_activity")
        async def create_expense_timeout_check(expense_id: str) -> None:
            # Check that we're called with 10 second timeout
            activity_info = activity.info()
            timeout_calls.append(("create", activity_info.start_to_close_timeout))
            return None

        @activity.defn(name="wait_for_decision_activity")
        async def wait_decision_timeout_check(expense_id: str) -> str:
            # Check that we're called with 10 minute timeout
            activity_info = activity.info()
            timeout_calls.append(("wait", activity_info.start_to_close_timeout))
            return "APPROVED"

        @activity.defn(name="payment_activity")
        async def payment_timeout_check(expense_id: str) -> None:
            # Check that we're called with 10 second timeout
            activity_info = activity.info()
            timeout_calls.append(("payment", activity_info.start_to_close_timeout))
            return None

        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[SampleExpenseWorkflow],
            activities=[
                create_expense_timeout_check,
                wait_decision_timeout_check,
                payment_timeout_check,
            ],
        ):
            await client.execute_workflow(
                SampleExpenseWorkflow.run,
                "test-expense-timeouts",
                id=f"test-workflow-timeouts-{uuid.uuid4()}",
                task_queue=task_queue,
            )

            # Verify timeout configurations
            assert len(timeout_calls) == 3
            create_timeout = next(
                call[1] for call in timeout_calls if call[0] == "create"
            )
            wait_timeout = next(call[1] for call in timeout_calls if call[0] == "wait")
            payment_timeout = next(
                call[1] for call in timeout_calls if call[0] == "payment"
            )

            assert create_timeout == timedelta(seconds=10)
            assert wait_timeout == timedelta(minutes=10)
            assert payment_timeout == timedelta(seconds=10)


class TestWorkflowFromSimpleFile:
    """Tests moved from the original simple test_workflow.py file"""

    async def test_workflow_with_mock_activities(
        self, client: Client, env: WorkflowEnvironment
    ):
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

    async def test_workflow_rejected_expense(
        self, client: Client, env: WorkflowEnvironment
    ):
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
