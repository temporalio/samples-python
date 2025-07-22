"""
Tests for individual expense activities.
Focuses on activity behavior, parameters, error handling, and HTTP interactions.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from temporalio.testing import ActivityEnvironment

from expense import EXPENSE_SERVER_HOST_PORT
from expense.activities import (
    create_expense_activity,
    payment_activity,
    register_for_decision_activity,
)


class TestCreateExpenseActivity:
    """Test create_expense_activity individual behavior"""

    @pytest.fixture
    def activity_env(self):
        return ActivityEnvironment()

    async def test_create_expense_activity_success(self, activity_env):
        """Test successful expense creation"""
        with patch("expense.activities.get_http_client") as mock_get_client:
            # Mock successful HTTP response
            mock_response = AsyncMock()
            mock_response.text = "SUCCEED"
            mock_response.raise_for_status = AsyncMock()

            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_get_client.return_value = mock_client_instance

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
        with patch("expense.activities.get_http_client") as mock_get_client:
            # Mock HTTP error with proper response mock
            mock_response_obj = MagicMock()
            mock_response_obj.status_code = 500
            mock_response_obj.text = "Server Error"

            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Server Error", request=MagicMock(), response=mock_response_obj
            )

            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_get_client.return_value = mock_client_instance

            with pytest.raises(httpx.HTTPStatusError):
                await activity_env.run(create_expense_activity, "test-expense-123")

    async def test_create_expense_activity_server_error_response(self, activity_env):
        """Test create expense activity with server error response"""
        with patch("expense.activities.get_http_client") as mock_get_client:
            # Mock error response
            mock_response = AsyncMock()
            mock_response.text = "ERROR:ID_ALREADY_EXISTS"
            mock_response.raise_for_status = AsyncMock()

            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_get_client.return_value = mock_client_instance

            with pytest.raises(Exception, match="ERROR:ID_ALREADY_EXISTS"):
                await activity_env.run(create_expense_activity, "test-expense-123")


class TestRegisterForDecisionActivity:
    """Test register_for_decision_activity individual behavior"""

    @pytest.fixture
    def activity_env(self):
        return ActivityEnvironment()

    async def test_register_for_decision_activity_empty_id(self, activity_env):
        """Test register for decision activity with empty expense ID"""
        with pytest.raises(ValueError, match="expense id is empty"):
            await activity_env.run(register_for_decision_activity, "")

    async def test_register_for_decision_activity_success(self, activity_env):
        """Test successful expense registration behavior"""
        # Mock the HTTP client and response
        mock_response = AsyncMock()
        mock_response.raise_for_status = AsyncMock()

        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response

        # Mock the get_http_client function
        with patch("expense.activities.get_http_client", return_value=mock_http_client):
            result = await activity_env.run(
                register_for_decision_activity, "test-expense-123"
            )

            # Activity should return None on success
            assert result is None

            # Verify HTTP registration was called
            mock_http_client.post.assert_called_once()
            call_args = mock_http_client.post.call_args
            assert "/registerWorkflow" in call_args[0][0]
            assert call_args[1]["params"]["id"] == "test-expense-123"
            assert "workflow_id" in call_args[1]["data"]


class TestPaymentActivity:
    """Test payment_activity individual behavior"""

    @pytest.fixture
    def activity_env(self):
        return ActivityEnvironment()

    async def test_payment_activity_success(self, activity_env):
        """Test successful payment processing"""
        with patch("expense.activities.get_http_client") as mock_get_client:
            # Mock successful payment response
            mock_response = AsyncMock()
            mock_response.text = "SUCCEED"
            mock_response.raise_for_status = AsyncMock()

            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_get_client.return_value = mock_client_instance

            # Execute activity
            result = await activity_env.run(payment_activity, "test-expense-123")

            # Verify HTTP call
            mock_client_instance.post.assert_called_once_with(
                f"{EXPENSE_SERVER_HOST_PORT}/action",
                data={
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
        with patch("expense.activities.get_http_client") as mock_get_client:
            # Mock payment failure response
            mock_response = AsyncMock()
            mock_response.text = "ERROR:INSUFFICIENT_FUNDS"
            mock_response.raise_for_status = AsyncMock()

            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_get_client.return_value = mock_client_instance

            with pytest.raises(Exception, match="ERROR:INSUFFICIENT_FUNDS"):
                await activity_env.run(payment_activity, "test-expense-123")
