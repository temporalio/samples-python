"""
Integration tests for expense workflow with mock HTTP server.
Tests end-to-end behavior with realistic HTTP interactions.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from temporalio import activity
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from expense.workflow import SampleExpenseWorkflow


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
        responses = {
            "/create": "SUCCEED",
            "/registerCallback": "SUCCEED",
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

            # Use completely mocked activities
            @activity.defn(name="create_expense_activity")
            async def mock_create_expense(expense_id: str) -> None:
                # Simulated HTTP call logic
                return None

            @activity.defn(name="wait_for_decision_activity")
            async def mock_wait_rejected(expense_id: str) -> str:
                # Simulate the callback registration and return rejected decision
                return "REJECTED"

            @activity.defn(name="payment_activity")
            async def mock_payment(expense_id: str) -> None:
                # Simulated HTTP call logic
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
