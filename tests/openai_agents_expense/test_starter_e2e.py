"""
End-to-End Tests for OpenAI Agents Expense Processing Starter

This module contains comprehensive E2E tests that validate the complete workflow
from starter.py execution through workflow completion, including:
- All expense scenarios (1, 2, 3, all)
- Human-in-the-loop UI integration
- OpenAI API integration (using .env file)
- Full workflow execution with -w flag
"""

import asyncio
import os
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from temporalio.client import Client
from temporalio.contrib.openai_agents.open_ai_data_converter import (
    open_ai_data_converter,
)
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

# Import the components we're testing
from openai_agents_expense import TASK_QUEUE, WORKFLOW_ID_PREFIX
from openai_agents_expense.activities import (
    create_expense_activity,
    payment_activity,
    wait_for_decision_activity,
    web_search_activity,
)
from openai_agents_expense.models import ExpenseReport
from openai_agents_expense.ui import ExpenseReviewState, all_expenses, token_map
from openai_agents_expense.workflows.expense_workflow import ExpenseWorkflow


class TestStarterE2E:
    """End-to-end tests for starter.py scenarios"""

    @pytest.fixture(autouse=True)
    def setup_env(self):
        """Setup environment variables from .env file"""
        env_path = Path(__file__).parent.parent.parent / ".env"
        if env_path.exists():
            try:
                from dotenv import load_dotenv

                load_dotenv(env_path)
            except ImportError:
                # If python-dotenv is not available, read manually
                with open(env_path) as f:
                    for line in f:
                        if line.strip() and not line.startswith("#"):
                            key, value = line.strip().split("=", 1)
                            os.environ[key] = value

        # Ensure OpenAI API key is available
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not found in .env file")

    @pytest.fixture
    def mock_expense_server(self):
        """Mock the expense server HTTP endpoints"""

        class MockExpenseServer:
            def __init__(self):
                self.expenses = {}
                self.tokens = {}

            async def handle_request(self, method, url, **kwargs):
                """Handle HTTP requests to the expense server"""
                mock_response = AsyncMock()

                # Parse URL to determine endpoint
                if "/create" in url:
                    # Extract expense ID from params
                    if "params" in kwargs:
                        expense_id = kwargs["params"].get("id")
                        if expense_id:
                            if expense_id in self.expenses:
                                mock_response.text = "ERROR:ID_ALREADY_EXISTS"
                            else:
                                self.expenses[
                                    expense_id
                                ] = ExpenseReviewState.REQUIRES_REVIEW
                                mock_response.text = "SUCCEED"
                        else:
                            mock_response.text = "ERROR:MISSING_ID"
                    else:
                        mock_response.text = "SUCCEED"

                elif "/registerCallback" in url:
                    mock_response.text = "SUCCEED"

                elif "/action" in url:
                    # Handle payment processing
                    if "params" in kwargs:
                        action_type = kwargs["params"].get("type")
                        expense_id = kwargs["params"].get("id")
                        if action_type == "payment" and expense_id:
                            if expense_id in self.expenses:
                                self.expenses[expense_id] = ExpenseReviewState.PAID
                                mock_response.text = "SUCCEED"
                            else:
                                mock_response.text = "ERROR:INVALID_ID"
                        else:
                            mock_response.text = "SUCCEED"
                    else:
                        mock_response.text = "SUCCEED"

                else:
                    mock_response.text = "NOT_FOUND"

                mock_response.raise_for_status = AsyncMock()
                mock_response.status_code = 200
                return mock_response

        return MockExpenseServer()

    @pytest.fixture
    def mock_human_decision(self):
        """Mock human decision for expenses that require human review"""

        class MockHumanDecision:
            def __init__(self):
                self.decisions = {
                    # Expense 2 (international travel) - approve
                    "EXP-2024-002": "APPROVED",
                    # Expense 3 (suspicious vendor) - reject
                    "EXP-2024-003": "REJECTED_SUSPICIOUS_VENDOR",
                }

            async def make_decision(self, expense_id: str) -> str:
                """Simulate human decision making"""
                await asyncio.sleep(0.1)  # Simulate decision time
                return self.decisions.get(expense_id, "APPROVED")

        return MockHumanDecision()

    @pytest.mark.asyncio
    async def test_expense_1_auto_approval(self, mock_expense_server):
        """Test expense 1 (office supplies) - should auto-approve"""

        # Clear any existing state
        all_expenses.clear()
        token_map.clear()

        # Mock HTTP client
        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.get.side_effect = mock_expense_server.handle_request
            mock_client_instance.post.side_effect = mock_expense_server.handle_request
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            # Connect to Temporal server
            client = await Client.connect(
                "localhost:7233", data_converter=open_ai_data_converter
            )

            # Start worker in background
            task_queue = f"{TASK_QUEUE}-test-{uuid.uuid4()}"

            async with Worker(
                client,
                task_queue=task_queue,
                workflows=[ExpenseWorkflow],
                activities=[
                    create_expense_activity,
                    wait_for_decision_activity,
                    payment_activity,
                    web_search_activity,
                ],
            ):
                # Create sample expense (office supplies - should auto-approve)
                expense = ExpenseReport(
                    expense_id="EXP-2024-001",
                    amount=Decimal("45.00"),
                    description="Office supplies for Q4 planning",
                    vendor="Staples Inc",
                    date=date(2024, 1, 15),
                    department="Marketing",
                    employee_id="EMP-001",
                    receipt_provided=True,
                    submission_date=date(2024, 1, 16),
                    client_name=None,
                    business_justification=None,
                    is_international_travel=False,
                )

                # Start workflow
                workflow_id = (
                    f"{WORKFLOW_ID_PREFIX}-{expense.expense_id}-{uuid.uuid4()}"
                )
                handle = await client.start_workflow(
                    ExpenseWorkflow.run,
                    expense,
                    id=workflow_id,
                    task_queue=task_queue,
                )

                # Wait for completion
                result = await handle.result()

                # Verify results
                assert result == "COMPLETED"

                # Check final status
                status = await handle.query(ExpenseWorkflow.get_status)
                assert status.current_status in ["paid", "approved"]

    @pytest.mark.asyncio
    async def test_expense_2_human_approval(
        self, mock_expense_server, mock_human_decision
    ):
        """Test expense 2 (international travel) - should escalate to human then approve"""

        # Clear any existing state
        all_expenses.clear()
        token_map.clear()

        # Mock HTTP client
        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.get.side_effect = mock_expense_server.handle_request
            mock_client_instance.post.side_effect = mock_expense_server.handle_request
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            # Mock the wait_for_decision_activity to simulate human approval
            original_wait_activity = wait_for_decision_activity

            async def mock_wait_for_decision(expense_id: str) -> str:
                # Simulate human decision
                return await mock_human_decision.make_decision(expense_id)

            with patch(
                "openai_agents_expense.activities.expense_activities.wait_for_decision_activity",
                mock_wait_for_decision,
            ):
                # Connect to Temporal server
                client = await Client.connect(
                    "localhost:7233", data_converter=open_ai_data_converter
                )

                # Start worker in background
                task_queue = f"{TASK_QUEUE}-test-{uuid.uuid4()}"

                async with Worker(
                    client,
                    task_queue=task_queue,
                    workflows=[ExpenseWorkflow],
                    activities=[
                        create_expense_activity,
                        mock_wait_for_decision,
                        payment_activity,
                        web_search_activity,
                    ],
                ):
                    # Create sample expense (international travel - should escalate)
                    expense = ExpenseReport(
                        expense_id="EXP-2024-002",
                        amount=Decimal("400.00"),
                        description="Flight to London for client meeting",
                        vendor="British Airways",
                        date=date(2024, 1, 20),
                        department="Sales",
                        employee_id="EMP-002",
                        receipt_provided=True,
                        submission_date=date(2024, 1, 21),
                        client_name="Global Tech Partners UK",
                        business_justification="Quarterly business review meeting with key client",
                        is_international_travel=True,
                    )

                    # Start workflow
                    workflow_id = (
                        f"{WORKFLOW_ID_PREFIX}-{expense.expense_id}-{uuid.uuid4()}"
                    )
                    handle = await client.start_workflow(
                        ExpenseWorkflow.run,
                        expense,
                        id=workflow_id,
                        task_queue=task_queue,
                    )

                    # Wait for completion
                    result = await handle.result()

                    # Verify results
                    assert result == "COMPLETED"

    @pytest.mark.asyncio
    async def test_expense_3_human_rejection(
        self, mock_expense_server, mock_human_decision
    ):
        """Test expense 3 (suspicious vendor) - should escalate to human then reject"""

        # Clear any existing state
        all_expenses.clear()
        token_map.clear()

        # Mock HTTP client
        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.get.side_effect = mock_expense_server.handle_request
            mock_client_instance.post.side_effect = mock_expense_server.handle_request
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            # Mock the wait_for_decision_activity to simulate human rejection
            async def mock_wait_for_decision(expense_id: str) -> str:
                return await mock_human_decision.make_decision(expense_id)

            with patch(
                "openai_agents_expense.activities.expense_activities.wait_for_decision_activity",
                mock_wait_for_decision,
            ):
                # Connect to Temporal server
                client = await Client.connect(
                    "localhost:7233", data_converter=open_ai_data_converter
                )

                # Start worker in background
                task_queue = f"{TASK_QUEUE}-test-{uuid.uuid4()}"

                async with Worker(
                    client,
                    task_queue=task_queue,
                    workflows=[ExpenseWorkflow],
                    activities=[
                        create_expense_activity,
                        mock_wait_for_decision,
                        payment_activity,
                        web_search_activity,
                    ],
                ):
                    # Create sample expense (suspicious vendor - should escalate and reject)
                    expense = ExpenseReport(
                        expense_id="EXP-2024-003",
                        amount=Decimal("200.00"),
                        description="Team dinner after project completion",
                        vendor="Joe's Totally Legit Restaurant LLC",
                        date=date(2024, 1, 8),
                        department="Engineering",
                        employee_id="EMP-003",
                        receipt_provided=True,
                        submission_date=date(2024, 1, 9),
                        client_name=None,
                        business_justification="Team celebration dinner following successful product launch",
                        is_international_travel=False,
                    )

                    # Start workflow
                    workflow_id = (
                        f"{WORKFLOW_ID_PREFIX}-{expense.expense_id}-{uuid.uuid4()}"
                    )
                    handle = await client.start_workflow(
                        ExpenseWorkflow.run,
                        expense,
                        id=workflow_id,
                        task_queue=task_queue,
                    )

                    # Wait for completion
                    result = await handle.result()

                    # Verify results
                    assert result == "REJECTED"

    @pytest.mark.asyncio
    async def test_all_expenses_batch_processing(
        self, mock_expense_server, mock_human_decision
    ):
        """Test processing all expenses in batch with -e all -w"""

        # Clear any existing state
        all_expenses.clear()
        token_map.clear()

        # Mock HTTP client
        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.get.side_effect = mock_expense_server.handle_request
            mock_client_instance.post.side_effect = mock_expense_server.handle_request
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            # Mock the wait_for_decision_activity for human decisions
            async def mock_wait_for_decision(expense_id: str) -> str:
                return await mock_human_decision.make_decision(expense_id)

            with patch(
                "openai_agents_expense.activities.expense_activities.wait_for_decision_activity",
                mock_wait_for_decision,
            ):
                # Connect to Temporal server
                client = await Client.connect(
                    "localhost:7233", data_converter=open_ai_data_converter
                )

                # Start worker in background
                task_queue = f"{TASK_QUEUE}-test-{uuid.uuid4()}"

                async with Worker(
                    client,
                    task_queue=task_queue,
                    workflows=[ExpenseWorkflow],
                    activities=[
                        create_expense_activity,
                        mock_wait_for_decision,
                        payment_activity,
                        web_search_activity,
                    ],
                ):
                    # Create all sample expenses
                    expenses = [
                        # Expense 1: Office supplies - should auto-approve
                        ExpenseReport(
                            expense_id="EXP-2024-001",
                            amount=Decimal("45.00"),
                            description="Office supplies for Q4 planning",
                            vendor="Staples Inc",
                            date=date(2024, 1, 15),
                            department="Marketing",
                            employee_id="EMP-001",
                            receipt_provided=True,
                            submission_date=date(2024, 1, 16),
                            client_name=None,
                            business_justification=None,
                            is_international_travel=False,
                        ),
                        # Expense 2: International travel - should escalate then approve
                        ExpenseReport(
                            expense_id="EXP-2024-002",
                            amount=Decimal("400.00"),
                            description="Flight to London for client meeting",
                            vendor="British Airways",
                            date=date(2024, 1, 20),
                            department="Sales",
                            employee_id="EMP-002",
                            receipt_provided=True,
                            submission_date=date(2024, 1, 21),
                            client_name="Global Tech Partners UK",
                            business_justification="Quarterly business review meeting with key client",
                            is_international_travel=True,
                        ),
                        # Expense 3: Suspicious vendor - should escalate then reject
                        ExpenseReport(
                            expense_id="EXP-2024-003",
                            amount=Decimal("200.00"),
                            description="Team dinner after project completion",
                            vendor="Joe's Totally Legit Restaurant LLC",
                            date=date(2024, 1, 8),
                            department="Engineering",
                            employee_id="EMP-003",
                            receipt_provided=True,
                            submission_date=date(2024, 1, 9),
                            client_name=None,
                            business_justification="Team celebration dinner following successful product launch",
                            is_international_travel=False,
                        ),
                    ]

                    # Start workflows for all expenses
                    handles = []
                    for expense in expenses:
                        workflow_id = (
                            f"{WORKFLOW_ID_PREFIX}-{expense.expense_id}-{uuid.uuid4()}"
                        )
                        handle = await client.start_workflow(
                            ExpenseWorkflow.run,
                            expense,
                            id=workflow_id,
                            task_queue=task_queue,
                        )
                        handles.append((handle, expense))

                    # Wait for all completions
                    results = []
                    for handle, expense in handles:
                        result = await handle.result()
                        results.append((expense.expense_id, result))

                    # Verify results
                    expected_results = {
                        "EXP-2024-001": "COMPLETED",  # Auto-approved
                        "EXP-2024-002": "COMPLETED",  # Human approved
                        "EXP-2024-003": "REJECTED",  # Human rejected
                    }

                    for expense_id, result in results:
                        assert (
                            result == expected_results[expense_id]
                        ), f"Unexpected result for {expense_id}: {result}"

    @pytest.mark.asyncio
    async def test_starter_integration_expense_1(self):
        """Test calling starter.py directly for expense 1 with mocked components"""

        # Mock sys.argv to simulate command line arguments
        with patch("sys.argv", ["starter.py", "-e", "1", "-w"]):
            # Mock the main workflow execution
            with patch("openai_agents_expense.starter.Client.connect") as mock_connect:
                with patch(
                    "openai_agents_expense.starter.Client.start_workflow"
                ) as mock_start:
                    # Mock client and handle
                    mock_client = AsyncMock()
                    mock_connect.return_value = mock_client

                    mock_handle = AsyncMock()
                    mock_handle.result.return_value = "COMPLETED"
                    mock_handle.query.return_value = AsyncMock(current_status="paid")
                    mock_start.return_value = mock_handle

                    # Mock the expense processing
                    with patch("openai_agents_expense.starter.ExpenseWorkflow"):
                        # This should run without errors
                        try:
                            await starter_main()
                            # If we get here, the test passed
                            assert True
                        except Exception as e:
                            pytest.fail(f"starter_main() raised an exception: {e}")

    @pytest.mark.asyncio
    async def test_ui_integration_mock_server(self):
        """Test the expense UI server integration"""

        # Test that the UI server endpoints work correctly
        from fastapi.testclient import TestClient

        from openai_agents_expense.ui import app

        client = TestClient(app)

        # Test home page
        response = client.get("/")
        assert response.status_code == 200
        assert "OpenAI Agents Expense System" in response.text

        # Test creating an expense
        response = client.get("/create?id=test-expense&is_api_call=true")
        assert response.status_code == 200
        assert response.text == "SUCCEED"

        # Test status check
        response = client.get("/status?id=test-expense")
        assert response.status_code == 200
        assert response.text == "CREATED"

        # Test approval action
        response = client.get("/action?type=approve&id=test-expense&is_api_call=true")
        assert response.status_code == 200
        assert response.text == "SUCCEED"

        # Test payment action
        response = client.get("/action?type=payment&id=test-expense&is_api_call=true")
        assert response.status_code == 200
        assert response.text == "SUCCEED"

    def test_environment_setup(self):
        """Test that the environment is properly configured"""

        # Check that .env file exists
        env_path = Path(__file__).parent.parent.parent / ".env"
        assert env_path.exists(), ".env file not found in samples-python-2/"

        # Check that OpenAI API key is available
        assert os.getenv("OPENAI_API_KEY"), "OPENAI_API_KEY not found in environment"

        # Check that required modules can be imported
        try:
            from openai_agents_expense.models import ExpenseReport
            from openai_agents_expense.starter import main
            from openai_agents_expense.workflows.expense_workflow import ExpenseWorkflow

            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import required modules: {e}")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
