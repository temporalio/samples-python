"""
Tests for the SampleExpenseWorkflow orchestration logic.
Focuses on workflow behavior, decision paths, and error propagation.
"""

import asyncio
import uuid
from datetime import timedelta

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

    def schedule_decision(self, expense_id: str, decision: str):
        """Schedule a decision to be made (simulates human decision)"""
        self.scheduled_decisions[expense_id] = decision

        async def send_decision():
            try:
                if expense_id in self.workflow_map:
                    workflow_id = self.workflow_map[expense_id]
                    handle = self.client.get_workflow_handle(workflow_id)
                    await handle.signal("expense_decision_signal", decision)
            except Exception:
                # Ignore errors in time-skipping mode where workflows may complete quickly
                pass

        asyncio.create_task(send_decision())

    def create_register_activity(self):
        """Create a register activity that works with this mock UI"""

        @activity.defn(name="register_for_decision_activity")
        async def register_decision_activity(expense_id: str) -> None:
            # In time-skipping mode, send the decision immediately
            if expense_id in self.scheduled_decisions:
                decision = self.scheduled_decisions[expense_id]
                if expense_id in self.workflow_map:
                    workflow_id = self.workflow_map[expense_id]
                    handle = self.client.get_workflow_handle(workflow_id)
                    try:
                        # Send signal immediately when registering
                        await handle.signal("expense_decision_signal", decision)
                    except Exception:
                        # Ignore errors in time-skipping mode
                        pass
            return None

        return register_decision_activity


class TestWorkflowPaths:
    """Test main workflow execution paths"""

    async def test_workflow_approved_complete_flow(
        self, client: Client, env: WorkflowEnvironment
    ):
        """Test complete approved expense workflow - Happy Path"""
        task_queue = f"test-expense-approved-{uuid.uuid4()}"
        workflow_id = f"test-workflow-approved-{uuid.uuid4()}"
        expense_id = "test-expense-approved"

        # Set up mock UI
        mock_ui = MockExpenseUI(client)
        mock_ui.register_workflow(expense_id, workflow_id)
        mock_ui.schedule_decision(expense_id, "APPROVED")

        @activity.defn(name="create_expense_activity")
        async def create_expense_mock(expense_id: str) -> None:
            return None

        @activity.defn(name="payment_activity")
        async def payment_mock(expense_id: str) -> None:
            return None

        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[SampleExpenseWorkflow],
            activities=[
                create_expense_mock,
                mock_ui.create_register_activity(),
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

    async def test_workflow_rejected_flow(
        self, client: Client, env: WorkflowEnvironment
    ):
        """Test rejected expense workflow - Returns empty string"""
        task_queue = f"test-expense-rejected-{uuid.uuid4()}"
        workflow_id = f"test-workflow-rejected-{uuid.uuid4()}"
        expense_id = "test-expense-rejected"

        # Set up mock UI
        mock_ui = MockExpenseUI(client)
        mock_ui.register_workflow(expense_id, workflow_id)
        mock_ui.schedule_decision(expense_id, "REJECTED")

        @activity.defn(name="create_expense_activity")
        async def create_expense_mock(expense_id: str) -> None:
            return None

        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[SampleExpenseWorkflow],
            activities=[create_expense_mock, mock_ui.create_register_activity()],
        ):
            result = await client.execute_workflow(
                SampleExpenseWorkflow.run,
                expense_id,
                id=workflow_id,
                task_queue=task_queue,
            )

            assert result == ""

    async def test_workflow_other_decision_treated_as_rejected(
        self, client: Client, env: WorkflowEnvironment
    ):
        """Test that non-APPROVED decisions are treated as rejection"""
        task_queue = f"test-expense-other-{uuid.uuid4()}"
        workflow_id = f"test-workflow-other-{uuid.uuid4()}"
        expense_id = "test-expense-other"

        # Set up mock UI with PENDING decision
        mock_ui = MockExpenseUI(client)
        mock_ui.register_workflow(expense_id, workflow_id)
        mock_ui.schedule_decision(expense_id, "PENDING")  # Any non-APPROVED value

        @activity.defn(name="create_expense_activity")
        async def create_expense_mock(expense_id: str) -> None:
            return None

        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[SampleExpenseWorkflow],
            activities=[create_expense_mock, mock_ui.create_register_activity()],
        ):
            result = await client.execute_workflow(
                SampleExpenseWorkflow.run,
                expense_id,
                id=workflow_id,
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
            workflow_id = f"test-workflow-decision-{decision.lower()}-{uuid.uuid4()}"
            expense_id = f"test-expense-{decision.lower()}"

            # Set up mock UI with specific decision
            mock_ui = MockExpenseUI(client)
            mock_ui.register_workflow(expense_id, workflow_id)
            mock_ui.schedule_decision(expense_id, decision)

            @activity.defn(name="create_expense_activity")
            async def create_expense_mock(expense_id: str) -> None:
                return None

            @activity.defn(name="payment_activity")
            async def payment_mock(expense_id: str) -> None:
                return None

            async with Worker(
                client,
                task_queue=task_queue,
                workflows=[SampleExpenseWorkflow],
                activities=[
                    create_expense_mock,
                    mock_ui.create_register_activity(),
                    payment_mock,
                ],
            ):
                result = await client.execute_workflow(
                    SampleExpenseWorkflow.run,
                    expense_id,
                    id=workflow_id,
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

        @activity.defn(name="register_for_decision_activity")
        async def failing_wait_decision(expense_id: str) -> None:
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
        workflow_id = f"test-workflow-payment-fail-{uuid.uuid4()}"
        expense_id = "test-expense-payment-fail"

        # Set up mock UI with APPROVED decision
        mock_ui = MockExpenseUI(client)
        mock_ui.register_workflow(expense_id, workflow_id)
        mock_ui.schedule_decision(expense_id, "APPROVED")

        @activity.defn(name="create_expense_activity")
        async def create_expense_mock(expense_id: str) -> None:
            return None

        @activity.defn(name="payment_activity")
        async def failing_payment(expense_id: str):
            raise ApplicationError("Payment processing failed", non_retryable=True)

        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[SampleExpenseWorkflow],
            activities=[
                create_expense_mock,
                mock_ui.create_register_activity(),
                failing_payment,
            ],
        ):
            with pytest.raises(WorkflowFailureError):
                await client.execute_workflow(
                    SampleExpenseWorkflow.run,
                    expense_id,
                    id=workflow_id,
                    task_queue=task_queue,
                )


class TestWorkflowConfiguration:
    """Test workflow timeout and configuration behavior"""

    async def test_workflow_timeout_configuration(
        self, client: Client, env: WorkflowEnvironment
    ):
        """Test that workflow uses correct timeout configurations"""
        task_queue = f"test-timeouts-{uuid.uuid4()}"
        workflow_id = f"test-workflow-timeouts-{uuid.uuid4()}"
        expense_id = "test-expense-timeouts"
        timeout_calls = []

        # Set up mock UI with APPROVED decision
        mock_ui = MockExpenseUI(client)
        mock_ui.register_workflow(expense_id, workflow_id)
        mock_ui.schedule_decision(expense_id, "APPROVED")

        @activity.defn(name="create_expense_activity")
        async def create_expense_timeout_check(expense_id: str) -> None:
            # Check that we're called with 10 second timeout
            activity_info = activity.info()
            timeout_calls.append(("create", activity_info.start_to_close_timeout))
            return None

        @activity.defn(name="payment_activity")
        async def payment_timeout_check(expense_id: str) -> None:
            # Check that we're called with 10 second timeout
            activity_info = activity.info()
            timeout_calls.append(("payment", activity_info.start_to_close_timeout))
            return None

        # Create register activity that captures timeout info
        def create_timeout_checking_register_activity():
            @activity.defn(name="register_for_decision_activity")
            async def register_decision_timeout_check(expense_id: str) -> None:
                # Check that we're called with 10 minute timeout
                activity_info = activity.info()
                timeout_calls.append(("wait", activity_info.start_to_close_timeout))
                # Simulate automatic decision if one was scheduled
                if expense_id in mock_ui.scheduled_decisions:
                    # Decision will be sent by the scheduled task
                    pass
                return None

            return register_decision_timeout_check

        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[SampleExpenseWorkflow],
            activities=[
                create_expense_timeout_check,
                create_timeout_checking_register_activity(),
                payment_timeout_check,
            ],
        ):
            await client.execute_workflow(
                SampleExpenseWorkflow.run,
                expense_id,
                id=workflow_id,
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
            assert wait_timeout == timedelta(
                seconds=10
            )  # register activity timeout is 10 seconds
            assert payment_timeout == timedelta(seconds=10)


class TestWorkflowFromSimpleFile:
    """Tests moved from the original simple test_workflow.py file"""

    async def test_workflow_with_mock_activities(
        self, client: Client, env: WorkflowEnvironment
    ):
        """Test workflow with mocked activities"""
        task_queue = f"test-expense-{uuid.uuid4()}"
        workflow_id = f"test-expense-workflow-{uuid.uuid4()}"
        expense_id = "test-expense-id"

        # Set up mock UI with APPROVED decision
        mock_ui = MockExpenseUI(client)
        mock_ui.register_workflow(expense_id, workflow_id)
        mock_ui.schedule_decision(expense_id, "APPROVED")

        # Mock the activities to return expected values
        @activity.defn(name="create_expense_activity")
        async def create_expense_mock(expense_id: str) -> None:
            # Mock succeeds by returning None
            return None

        @activity.defn(name="payment_activity")
        async def payment_mock(expense_id: str) -> None:
            # Mock succeeds by returning None
            return None

        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[SampleExpenseWorkflow],
            activities=[
                create_expense_mock,
                mock_ui.create_register_activity(),
                payment_mock,
            ],
        ):
            # Execute workflow
            result = await client.execute_workflow(
                SampleExpenseWorkflow.run,
                expense_id,
                id=workflow_id,
                task_queue=task_queue,
            )

            # Verify result
            assert result == "COMPLETED"

    async def test_workflow_rejected_expense(
        self, client: Client, env: WorkflowEnvironment
    ):
        """Test workflow when expense is rejected"""
        task_queue = f"test-expense-rejected-{uuid.uuid4()}"
        workflow_id = f"test-expense-rejected-workflow-{uuid.uuid4()}"
        expense_id = "test-expense-id"

        # Set up mock UI with REJECTED decision
        mock_ui = MockExpenseUI(client)
        mock_ui.register_workflow(expense_id, workflow_id)
        mock_ui.schedule_decision(expense_id, "REJECTED")

        # Mock the activities
        @activity.defn(name="create_expense_activity")
        async def create_expense_mock(expense_id: str) -> None:
            # Mock succeeds by returning None
            return None

        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[SampleExpenseWorkflow],
            activities=[create_expense_mock, mock_ui.create_register_activity()],
        ):
            # Execute workflow
            result = await client.execute_workflow(
                SampleExpenseWorkflow.run,
                expense_id,
                id=workflow_id,
                task_queue=task_queue,
            )

            # Verify result is empty string when rejected
            assert result == ""
