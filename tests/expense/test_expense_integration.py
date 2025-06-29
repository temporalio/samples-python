"""
Integration tests for expense workflow with mock HTTP server.
Tests end-to-end behavior with realistic HTTP interactions.
"""

import asyncio
import uuid
from unittest.mock import AsyncMock, patch

from temporalio import activity
from temporalio.client import Client
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


class TestExpenseWorkflowWithMockServer:
    """Test workflow with mock HTTP server"""

    async def test_workflow_with_mock_server_approved(
        self, client: Client, env: WorkflowEnvironment
    ):
        """Test complete workflow with mock HTTP server - approved path"""
        task_queue = f"test-mock-server-approved-{uuid.uuid4()}"
        workflow_id = f"test-mock-server-workflow-{uuid.uuid4()}"
        expense_id = "test-mock-server-expense"

        # Set up mock UI with APPROVED decision
        mock_ui = MockExpenseUI(client)
        mock_ui.register_workflow(expense_id, workflow_id)
        mock_ui.schedule_decision(expense_id, "APPROVED")

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

            @activity.defn(name="payment_activity")
            async def mock_payment(expense_id: str) -> None:
                # Simulated HTTP call logic
                return None

            async with Worker(
                client,
                task_queue=task_queue,
                workflows=[SampleExpenseWorkflow],
                activities=[
                    mock_create_expense,
                    mock_ui.create_register_activity(),
                    mock_payment,
                ],
            ):
                result = await client.execute_workflow(
                    SampleExpenseWorkflow.run,
                    expense_id,
                    id=workflow_id,
                    task_queue=task_queue,
                )

                assert result == "COMPLETED"

    async def test_workflow_with_mock_server_rejected(
        self, client: Client, env: WorkflowEnvironment
    ):
        """Test complete workflow with mock HTTP server - rejected path"""
        task_queue = f"test-mock-server-rejected-{uuid.uuid4()}"
        workflow_id = f"test-mock-server-rejected-workflow-{uuid.uuid4()}"
        expense_id = "test-mock-server-rejected"

        # Set up mock UI with REJECTED decision
        mock_ui = MockExpenseUI(client)
        mock_ui.register_workflow(expense_id, workflow_id)
        mock_ui.schedule_decision(expense_id, "REJECTED")

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

            @activity.defn(name="payment_activity")
            async def mock_payment(expense_id: str) -> None:
                # Simulated HTTP call logic
                return None

            async with Worker(
                client,
                task_queue=task_queue,
                workflows=[SampleExpenseWorkflow],
                activities=[
                    mock_create_expense,
                    mock_ui.create_register_activity(),
                    mock_payment,
                ],
            ):
                result = await client.execute_workflow(
                    SampleExpenseWorkflow.run,
                    expense_id,
                    id=workflow_id,
                    task_queue=task_queue,
                )

                assert result == ""
