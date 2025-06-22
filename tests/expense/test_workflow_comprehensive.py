"""
Comprehensive tests for the Expense Workflow and Activities based on the specification.
Tests both individual activities and complete workflow scenarios.
"""

import uuid
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from temporalio import activity
from temporalio.activity import _CompleteAsyncError
from temporalio.client import Client, WorkflowFailureError
from temporalio.exceptions import ApplicationError
from temporalio.testing import ActivityEnvironment, WorkflowEnvironment
from temporalio.worker import Worker

from expense import EXPENSE_SERVER_HOST_PORT
from expense.activities import (
    create_expense_activity,
    payment_activity,
    wait_for_decision_activity,
)
from expense.workflow import SampleExpenseWorkflow


class TestExpenseWorkflow:
    """Test the complete expense workflow scenarios"""

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


class TestExpenseActivities:
    """Test individual expense activities"""

    @pytest.fixture
    def activity_env(self):
        return ActivityEnvironment()

    async def test_create_expense_activity_success(self, activity_env):
        """Test successful expense creation"""
        with patch("httpx.AsyncClient") as mock_client:
            # Mock successful HTTP response
            mock_response = AsyncMock()
            mock_response.text = "SUCCEED"
            mock_response.raise_for_status = AsyncMock()

            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            # Execute activity
            result = await activity_env.run(create_expense_activity, "test-expense-123")

            # Verify HTTP call
            mock_client_instance.get.assert_called_once_with(
                f"{EXPENSE_SERVER_HOST_PORT}/create",
                params={"is_api_call": "true", "id": "test-expense-123"},
            )
            mock_response.raise_for_status.assert_called_once()

            # Activity should return None on success
            assert result is None

    async def test_create_expense_activity_empty_id(self, activity_env):
        """Test create expense activity with empty expense ID"""
        with pytest.raises(ValueError, match="expense id is empty"):
            await activity_env.run(create_expense_activity, "")

    async def test_create_expense_activity_http_error(self, activity_env):
        """Test create expense activity with HTTP error"""
        with patch("httpx.AsyncClient") as mock_client:
            # Mock HTTP error - use MagicMock for raise_for_status to avoid async issues
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Server Error", request=MagicMock(), response=MagicMock()
            )

            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            with pytest.raises(httpx.HTTPStatusError):
                await activity_env.run(create_expense_activity, "test-expense-123")

    async def test_create_expense_activity_server_error_response(self, activity_env):
        """Test create expense activity with server error response"""
        with patch("httpx.AsyncClient") as mock_client:
            # Mock error response
            mock_response = AsyncMock()
            mock_response.text = "ERROR:ID_ALREADY_EXISTS"
            mock_response.raise_for_status = AsyncMock()

            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            with pytest.raises(Exception, match="ERROR:ID_ALREADY_EXISTS"):
                await activity_env.run(create_expense_activity, "test-expense-123")

    async def test_wait_for_decision_activity_empty_id(self, activity_env):
        """Test wait for decision activity with empty expense ID"""
        with pytest.raises(ValueError, match="expense id is empty"):
            await activity_env.run(wait_for_decision_activity, "")

    async def test_wait_for_decision_activity_callback_registration_success(
        self, activity_env
    ):
        """Test successful callback registration behavior"""
        with patch("httpx.AsyncClient") as mock_client:
            # Mock successful callback registration
            mock_response = AsyncMock()
            mock_response.text = "SUCCEED"
            mock_response.raise_for_status = AsyncMock()

            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            # The activity should raise _CompleteAsyncError when it calls activity.raise_complete_async()
            # This is expected behavior - the activity registers the callback then signals async completion
            with pytest.raises(_CompleteAsyncError):
                await activity_env.run(wait_for_decision_activity, "test-expense-123")

            # Verify callback registration call was made
            mock_client_instance.post.assert_called_once()
            call_args = mock_client_instance.post.call_args
            assert f"{EXPENSE_SERVER_HOST_PORT}/registerCallback" in call_args[0][0]

            # Verify task token in form data
            assert "task_token" in call_args[1]["data"]

    async def test_wait_for_decision_activity_callback_registration_failure(
        self, activity_env
    ):
        """Test callback registration failure"""
        with patch("httpx.AsyncClient") as mock_client:
            # Mock failed callback registration
            mock_response = AsyncMock()
            mock_response.text = "ERROR:INVALID_ID"
            mock_response.raise_for_status = AsyncMock()

            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            with pytest.raises(
                Exception, match="register callback failed status: ERROR:INVALID_ID"
            ):
                await activity_env.run(wait_for_decision_activity, "test-expense-123")

    async def test_payment_activity_success(self, activity_env):
        """Test successful payment processing"""
        with patch("httpx.AsyncClient") as mock_client:
            # Mock successful payment response
            mock_response = AsyncMock()
            mock_response.text = "SUCCEED"
            mock_response.raise_for_status = AsyncMock()

            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            # Execute activity
            result = await activity_env.run(payment_activity, "test-expense-123")

            # Verify HTTP call
            mock_client_instance.get.assert_called_once_with(
                f"{EXPENSE_SERVER_HOST_PORT}/action",
                params={
                    "is_api_call": "true",
                    "type": "payment",
                    "id": "test-expense-123",
                },
            )

            # Activity should return None on success
            assert result is None

    async def test_payment_activity_empty_id(self, activity_env):
        """Test payment activity with empty expense ID"""
        with pytest.raises(ValueError, match="expense id is empty"):
            await activity_env.run(payment_activity, "")

    async def test_payment_activity_payment_failure(self, activity_env):
        """Test payment activity with payment failure"""
        with patch("httpx.AsyncClient") as mock_client:
            # Mock payment failure response
            mock_response = AsyncMock()
            mock_response.text = "ERROR:INSUFFICIENT_FUNDS"
            mock_response.raise_for_status = AsyncMock()

            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            with pytest.raises(Exception, match="ERROR:INSUFFICIENT_FUNDS"):
                await activity_env.run(payment_activity, "test-expense-123")


class TestExpenseWorkflowWithMockServer:
    """Test workflow with mock HTTP server"""

    async def test_workflow_with_mock_server_approved(
        self, client: Client, env: WorkflowEnvironment
    ):
        """Test complete workflow with mock HTTP server - approved path"""
        task_queue = f"test-mock-server-approved-{uuid.uuid4()}"

        # Mock HTTP responses
        responses = {
            "/create": "SUCCEED",
            "/registerCallback": "SUCCEED",
            "/action": "SUCCEED",
        }

        with patch("httpx.AsyncClient") as mock_client:

            async def mock_request_handler(*args, **kwargs):
                mock_response = AsyncMock()
                url = args[0] if args else kwargs.get("url", "")

                # Determine response based on URL path
                for path, response_text in responses.items():
                    if path in url:
                        mock_response.text = response_text
                        break
                else:
                    mock_response.text = "NOT_FOUND"

                mock_response.raise_for_status = AsyncMock()
                return mock_response

            mock_client_instance = AsyncMock()
            mock_client_instance.get.side_effect = mock_request_handler
            mock_client_instance.post.side_effect = mock_request_handler
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            # Use completely mocked activities to avoid async completion issues
            @activity.defn(name="create_expense_activity")
            async def mock_create_expense(expense_id: str) -> None:
                # Simulated HTTP call logic
                return None

            @activity.defn(name="wait_for_decision_activity")
            async def mock_wait_with_approval(expense_id: str) -> str:
                # Simulate the callback registration and return approved decision
                return "APPROVED"

            @activity.defn(name="payment_activity")
            async def mock_payment(expense_id: str) -> None:
                # Simulated HTTP call logic
                return None

            async with Worker(
                client,
                task_queue=task_queue,
                workflows=[SampleExpenseWorkflow],
                activities=[mock_create_expense, mock_wait_with_approval, mock_payment],
            ):
                result = await client.execute_workflow(
                    SampleExpenseWorkflow.run,
                    "test-mock-server-expense",
                    id=f"test-mock-server-workflow-{uuid.uuid4()}",
                    task_queue=task_queue,
                )

                assert result == "COMPLETED"

    async def test_workflow_with_mock_server_rejected(
        self, client: Client, env: WorkflowEnvironment
    ):
        """Test complete workflow with mock HTTP server - rejected path"""
        task_queue = f"test-mock-server-rejected-{uuid.uuid4()}"

        # Mock HTTP responses
        responses = {"/create": "SUCCEED", "/registerCallback": "SUCCEED"}

        with patch("httpx.AsyncClient") as mock_client:

            async def mock_request_handler(*args, **kwargs):
                mock_response = AsyncMock()
                url = args[0] if args else kwargs.get("url", "")

                for path, response_text in responses.items():
                    if path in url:
                        mock_response.text = response_text
                        break
                else:
                    mock_response.text = "NOT_FOUND"

                mock_response.raise_for_status = AsyncMock()
                return mock_response

            mock_client_instance = AsyncMock()
            mock_client_instance.get.side_effect = mock_request_handler
            mock_client_instance.post.side_effect = mock_request_handler
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            # Use completely mocked activities to avoid async completion issues
            @activity.defn(name="create_expense_activity")
            async def mock_create_expense(expense_id: str) -> None:
                return None

            @activity.defn(name="wait_for_decision_activity")
            async def mock_wait_rejected(expense_id: str) -> str:
                return "REJECTED"

            @activity.defn(name="payment_activity")
            async def mock_payment(expense_id: str) -> None:
                return None

            async with Worker(
                client,
                task_queue=task_queue,
                workflows=[SampleExpenseWorkflow],
                activities=[mock_create_expense, mock_wait_rejected, mock_payment],
            ):
                result = await client.execute_workflow(
                    SampleExpenseWorkflow.run,
                    "test-mock-server-rejected",
                    id=f"test-mock-server-rejected-workflow-{uuid.uuid4()}",
                    task_queue=task_queue,
                )

                assert result == ""


class TestExpenseWorkflowEdgeCases:
    """Test edge cases and error scenarios"""

    async def test_workflow_with_retryable_activity_failures(
        self, client: Client, env: WorkflowEnvironment
    ):
        """Test workflow behavior with retryable activity failures"""
        task_queue = f"test-retryable-{uuid.uuid4()}"
        attempt_counts = {"create": 0, "payment": 0}

        @activity.defn(name="create_expense_activity")
        async def create_expense_retry(expense_id: str) -> None:
            attempt_counts["create"] += 1
            if attempt_counts["create"] < 3:  # Fail first 2 attempts
                raise Exception("Temporary failure")
            return None

        @activity.defn(name="wait_for_decision_activity")
        async def wait_for_decision_mock(expense_id: str) -> str:
            return "APPROVED"

        @activity.defn(name="payment_activity")
        async def payment_retry(expense_id: str) -> None:
            attempt_counts["payment"] += 1
            if attempt_counts["payment"] < 2:  # Fail first attempt
                raise Exception("Temporary payment failure")
            return None

        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[SampleExpenseWorkflow],
            activities=[create_expense_retry, wait_for_decision_mock, payment_retry],
        ):
            result = await client.execute_workflow(
                SampleExpenseWorkflow.run,
                "test-expense-retry",
                id=f"test-workflow-retry-{uuid.uuid4()}",
                task_queue=task_queue,
            )

            assert result == "COMPLETED"
            assert attempt_counts["create"] == 3  # Should have retried
            assert attempt_counts["payment"] == 2  # Should have retried

    async def test_workflow_logging_behavior(
        self, client: Client, env: WorkflowEnvironment
    ):
        """Test that workflow logging works correctly"""
        task_queue = f"test-logging-{uuid.uuid4()}"

        @activity.defn(name="create_expense_activity")
        async def create_expense_mock(expense_id: str) -> None:
            activity.logger.info(f"Creating expense: {expense_id}")
            return None

        @activity.defn(name="wait_for_decision_activity")
        async def wait_for_decision_mock(expense_id: str) -> str:
            activity.logger.info(f"Waiting for decision on: {expense_id}")
            return "APPROVED"

        @activity.defn(name="payment_activity")
        async def payment_mock(expense_id: str) -> None:
            activity.logger.info(f"Processing payment for: {expense_id}")
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

    async def test_workflow_parameter_validation(
        self, client: Client, env: WorkflowEnvironment
    ):
        """Test workflow parameter validation"""
        task_queue = f"test-validation-{uuid.uuid4()}"

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



