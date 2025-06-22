"""
Tests for individual expense activities.
Focuses on activity behavior, parameters, error handling, and HTTP interactions.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from temporalio import activity
from temporalio.activity import _CompleteAsyncError
from temporalio.testing import ActivityEnvironment

from expense import EXPENSE_SERVER_HOST_PORT
from expense.activities import (
    create_expense_activity,
    payment_activity,
    wait_for_decision_activity,
)


class TestCreateExpenseActivity:
    """Test create_expense_activity individual behavior"""

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


class TestWaitForDecisionActivity:
    """Test wait_for_decision_activity individual behavior"""

    @pytest.fixture
    def activity_env(self):
        return ActivityEnvironment()

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


class TestPaymentActivity:
    """Test payment_activity individual behavior"""

    @pytest.fixture
    def activity_env(self):
        return ActivityEnvironment()

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
