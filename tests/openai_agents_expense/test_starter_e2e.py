"""
Fixed E2E Tests for OpenAI Agents Expense Processing Starter

This module contains tests that properly mock AI agents to avoid hanging on real OpenAI API calls.
"""

import asyncio
import os
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from temporalio.client import Client
from temporalio.contrib.openai_agents.invoke_model_activity import ModelActivity
from temporalio.contrib.openai_agents.open_ai_data_converter import (
    open_ai_data_converter,
)
from temporalio.worker import Worker

# Import the components we're testing
from openai_agents_expense import TASK_QUEUE, WORKFLOW_ID_PREFIX
from openai_agents_expense.activities import (
    create_expense_activity,
    payment_activity,
    register_for_decision_activity,
    update_expense_activity,
    web_search_activity,
)
from openai_agents_expense.models import ExpenseReport
from openai_agents_expense.ui import all_expenses, token_map
from openai_agents_expense.workflows.expense_workflow import ExpenseWorkflow


class TestStarterE2EFixed:
    """Fixed end-to-end tests for starter.py scenarios with proper mocking"""

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

        # For testing, we don't require OpenAI API key since we mock everything
        if not os.getenv("OPENAI_API_KEY"):
            os.environ["OPENAI_API_KEY"] = "test-api-key"

    @pytest.fixture
    def mock_expense_server(self):
        """Mock the expense server HTTP endpoints"""

        class MockExpenseServer:
            def __init__(self):
                self.expenses = {}

            async def handle_request(self, url, **kwargs):
                """Handle HTTP requests to the expense server"""
                mock_response = AsyncMock()

                # Parse URL to determine endpoint
                if "/create/" in url:
                    expense_id = url.split("/create/")[-1].split("?")[0]
                    if expense_id:
                        self.expenses[expense_id] = "created"
                        mock_response.text = "SUCCEED"
                    else:
                        mock_response.text = "ERROR:MISSING_ID"

                elif "/update/" in url:
                    expense_id = url.split("/update/")[-1].split("?")[0]
                    if expense_id in self.expenses:
                        mock_response.text = "SUCCEED"
                    else:
                        mock_response.text = "ERROR:INVALID_ID"

                elif "/registerWorkflow" in url:
                    mock_response.text = "SUCCEED"

                elif "/action" in url:
                    # Handle payment processing
                    mock_response.text = "SUCCEED"

                else:
                    mock_response.text = "NOT_FOUND"

                mock_response.raise_for_status = AsyncMock()
                mock_response.status_code = 200
                return mock_response

        return MockExpenseServer()

    @pytest.mark.asyncio
    async def test_expense_1_auto_approval_fixed(self, mock_expense_server):
        """Test expense 1 (office supplies) - should auto-approve with mocks"""

        # Clear any existing state
        all_expenses.clear()
        token_map.clear()

        # Mock HTTP client for expense activities
        with patch(
            "openai_agents_expense.activities.expense_activities.get_http_client"
        ) as mock_get_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = mock_expense_server.handle_request
            mock_client_instance.post = mock_expense_server.handle_request
            mock_get_client.return_value = mock_client_instance

            # Mock Runner.run calls to avoid real OpenAI API calls
            with patch("agents.run.Runner.run") as mock_runner:
                # Setup mock responses that return actual data instead of coroutines
                from openai_agents_expense.models import (
                    AgentDecision,
                    ExpenseCategory,
                    ExpenseResponse,
                    FraudAssessment,
                    PolicyEvaluation,
                )

                def create_mock_result(data, model_class):
                    """Create a result object with the final_output as an actual model instance"""

                    class MockRunResult:
                        def __init__(self, final_output):
                            self.final_output = final_output

                    # Create an actual model instance
                    model_instance = model_class(**data)
                    return MockRunResult(model_instance)

                async def get_mock_response(agent, input=None, **kwargs):
                    agent_name = (
                        str(agent.name) if hasattr(agent, "name") else str(agent)
                    )

                    if "CategoryAgent" in agent_name:
                        return create_mock_result(
                            {
                                "category": "Office Supplies",
                                "confidence": 0.95,
                                "reasoning": "Office supplies from Staples, confirmed legitimate vendor",
                                "vendor_validation": {
                                    "vendor_name": "Staples Inc",
                                    "is_legitimate": True,
                                    "confidence_score": 0.98,
                                    "web_search_summary": "Major office supply retailer with verified website",
                                },
                            },
                            ExpenseCategory,
                        )
                    elif "PolicyEvaluationAgent" in agent_name:
                        return create_mock_result(
                            {
                                "compliant": True,
                                "violations": [],
                                "reasoning": "Office supplies under $75, compliant with all policies",
                                "requires_human_review": False,
                                "policy_explanation": "No policy violations detected",
                                "confidence": 0.95,
                            },
                            PolicyEvaluation,
                        )
                    elif "FraudAgent" in agent_name:
                        return create_mock_result(
                            {
                                "overall_risk": "low",
                                "flags": [],
                                "reasoning": "Low risk expense from verified vendor with no fraud indicators",
                                "requires_human_review": False,
                                "confidence": 0.98,
                                "vendor_risk_indicators": [],
                            },
                            FraudAssessment,
                        )
                    elif "DecisionOrchestrationAgent" in agent_name:
                        return create_mock_result(
                            {
                                "decision": "approved",
                                "internal_reasoning": "Low risk office supplies from legitimate vendor with no fraud indicators",
                                "external_reasoning": "Approved - routine office supplies from verified vendor",
                                "escalation_reason": None,
                                "is_mandatory_escalation": False,
                                "confidence": 0.95,
                            },
                            AgentDecision,
                        )
                    elif "ResponseAgent" in agent_name:
                        return create_mock_result(
                            {
                                "decision_summary": "Your expense has been approved and processed for payment",
                                "policy_explanation": "Office supplies under $75 are automatically approved when from verified vendors",
                                "categorization_summary": "Categorized as Office Supplies from legitimate vendor Staples Inc",
                            },
                            ExpenseResponse,
                        )
                    else:
                        # Default response - just return a simple result
                        class MockRunResult:
                            def __init__(self, final_output):
                                self.final_output = final_output

                        return MockRunResult({"status": "completed"})

                mock_runner.side_effect = get_mock_response

                # Connect to Temporal server
                client = await Client.connect(
                    "localhost:7233", data_converter=open_ai_data_converter
                )

                # Start worker in background with unique task queue
                task_queue = f"{TASK_QUEUE}-test-{uuid.uuid4()}"

                # Initialize ModelActivity for LLM invocation
                model_activity = ModelActivity()

                async with Worker(
                    client,
                    task_queue=task_queue,
                    workflows=[ExpenseWorkflow],
                    activities=[
                        model_activity.invoke_model_activity,
                        create_expense_activity,
                        register_for_decision_activity,
                        payment_activity,
                        update_expense_activity,
                        web_search_activity,
                    ],
                ):
                    # Create sample expense (office supplies - should auto-approve)
                    expense = ExpenseReport(
                        expense_id="EXP-TEST-001",
                        amount=Decimal("45.00"),
                        description="Office supplies for Q4 planning",
                        vendor="Staples Inc",
                        expense_date=date(2024, 1, 15),
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

                    # Wait for completion with timeout
                    try:
                        result = await asyncio.wait_for(handle.result(), timeout=30.0)

                        # Verify results
                        assert (
                            "approved" in result.lower()
                            or "paid" in result.lower()
                            or "completed" in result.lower()
                        )

                        # Check final status
                        status = await handle.query(ExpenseWorkflow.get_status)
                        assert status.current_status in ["paid", "approved"]

                    except asyncio.TimeoutError:
                        pytest.fail("Workflow did not complete within 30 seconds")

    @pytest.mark.asyncio
    async def test_expense_2_international_travel_fixed(self, mock_expense_server):
        """Test expense 2 (international travel) - should require human approval with mocks"""

        # Clear any existing state
        all_expenses.clear()
        token_map.clear()

        # Mock HTTP client for expense activities
        with patch(
            "openai_agents_expense.activities.expense_activities.get_http_client"
        ) as mock_get_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = mock_expense_server.handle_request
            mock_client_instance.post = mock_expense_server.handle_request
            mock_get_client.return_value = mock_client_instance

            # Mock Runner.run calls to avoid real OpenAI API calls
            with patch("agents.run.Runner.run") as mock_runner:
                # Setup mock responses for international travel scenario
                from openai_agents_expense.models import (
                    AgentDecision,
                    ExpenseCategory,
                    ExpenseResponse,
                    FraudAssessment,
                    PolicyEvaluation,
                )

                def create_mock_result(data, model_class):
                    """Create a result object with the final_output as an actual model instance"""

                    class MockRunResult:
                        def __init__(self, final_output):
                            self.final_output = final_output

                    # Create an actual model instance
                    model_instance = model_class(**data)
                    return MockRunResult(model_instance)

                async def get_mock_response(agent, input=None, **kwargs):
                    agent_name = (
                        str(agent.name) if hasattr(agent, "name") else str(agent)
                    )

                    if "CategoryAgent" in agent_name:
                        return create_mock_result(
                            {
                                "category": "Travel & Transportation",
                                "confidence": 0.98,
                                "reasoning": "International flight booking for business travel",
                                "vendor_validation": {
                                    "vendor_name": "British Airways",
                                    "is_legitimate": True,
                                    "confidence_score": 0.99,
                                    "web_search_summary": "Major international airline with verified website",
                                },
                            },
                            ExpenseCategory,
                        )
                    elif "PolicyEvaluationAgent" in agent_name:
                        return create_mock_result(
                            {
                                "compliant": False,
                                "violations": [
                                    {
                                        "rule_name": "INTERNATIONAL TRAVEL",
                                        "violation_type": "mandatory_review",
                                        "severity": "requires_review",
                                        "details": "All international travel requires human approval",
                                        "threshold_amount": None,
                                    }
                                ],
                                "reasoning": "International travel requires mandatory human review",
                                "requires_human_review": True,
                                "policy_explanation": "All international travel expenses require human approval",
                                "confidence": 0.98,
                            },
                            PolicyEvaluation,
                        )
                    elif "FraudAgent" in agent_name:
                        return create_mock_result(
                            {
                                "overall_risk": "low",
                                "flags": [],
                                "reasoning": "Legitimate airline booking with no fraud indicators",
                                "requires_human_review": False,
                                "confidence": 0.95,
                                "vendor_risk_indicators": [],
                            },
                            FraudAssessment,
                        )
                    elif "DecisionOrchestrationAgent" in agent_name:
                        return create_mock_result(
                            {
                                "decision": "requires_human_review",
                                "internal_reasoning": "International travel requires human approval per policy",
                                "external_reasoning": "International travel expenses require human approval",
                                "escalation_reason": "International travel policy requires human review",
                                "is_mandatory_escalation": True,
                                "confidence": 0.98,
                            },
                            AgentDecision,
                        )
                    elif "ResponseAgent" in agent_name:
                        return create_mock_result(
                            {
                                "decision_summary": "Your expense has been escalated for human review due to international travel policy",
                                "policy_explanation": "All international travel expenses require human approval regardless of amount",
                                "categorization_summary": "Categorized as Travel & Transportation from legitimate airline British Airways",
                            },
                            ExpenseResponse,
                        )
                    else:
                        # Default response
                        class MockRunResult:
                            def __init__(self, final_output):
                                self.final_output = final_output

                        return MockRunResult({"status": "completed"})

                mock_runner.side_effect = get_mock_response

                # Connect to Temporal server
                client = await Client.connect(
                    "localhost:7233", data_converter=open_ai_data_converter
                )

                # Start worker in background with unique task queue
                task_queue = f"{TASK_QUEUE}-test-{uuid.uuid4()}"

                # Initialize ModelActivity for LLM invocation
                model_activity = ModelActivity()

                async with Worker(
                    client,
                    task_queue=task_queue,
                    workflows=[ExpenseWorkflow],
                    activities=[
                        model_activity.invoke_model_activity,
                        create_expense_activity,
                        register_for_decision_activity,
                        payment_activity,
                        update_expense_activity,
                        web_search_activity,
                    ],
                ):
                    # Create international travel expense
                    expense = ExpenseReport(
                        expense_id="EXP-TEST-002",
                        amount=Decimal("400.00"),
                        description="Flight to London for client meeting",
                        vendor="British Airways",
                        expense_date=date(2024, 1, 20),
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

                    # Wait a bit for workflow to process and reach waiting state
                    await asyncio.sleep(1.0)

                    # Simulate human approval via signal
                    await handle.signal("expense_decision_signal", "approved")

                    # Wait for completion with timeout
                    try:
                        result = await asyncio.wait_for(handle.result(), timeout=30.0)

                        # Verify results
                        assert result is not None

                        # Check final status
                        status = await handle.query(ExpenseWorkflow.get_status)
                        assert status.current_status in ["paid", "approved"]

                    except asyncio.TimeoutError:
                        pytest.fail("Workflow did not complete within 30 seconds")

    @pytest.mark.asyncio
    async def test_expense_3_suspicious_vendor_fixed(self, mock_expense_server):
        """Test expense 3 (suspicious vendor) - should be rejected with mocks"""

        # Clear any existing state
        all_expenses.clear()
        token_map.clear()

        # Mock HTTP client for expense activities
        with patch(
            "openai_agents_expense.activities.expense_activities.get_http_client"
        ) as mock_get_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = mock_expense_server.handle_request
            mock_client_instance.post = mock_expense_server.handle_request
            mock_get_client.return_value = mock_client_instance

            # Mock Runner.run calls to avoid real OpenAI API calls
            with patch("agents.run.Runner.run") as mock_runner:
                # Setup mock responses for suspicious vendor scenario
                from openai_agents_expense.models import (
                    AgentDecision,
                    ExpenseCategory,
                    ExpenseResponse,
                    FraudAssessment,
                    PolicyEvaluation,
                )

                def create_mock_result(data, model_class):
                    """Create a result object with the final_output as an actual model instance"""

                    class MockRunResult:
                        def __init__(self, final_output):
                            self.final_output = final_output

                    # Create an actual model instance
                    model_instance = model_class(**data)
                    return MockRunResult(model_instance)

                async def get_mock_response(agent, input=None, **kwargs):
                    agent_name = (
                        str(agent.name) if hasattr(agent, "name") else str(agent)
                    )

                    if "CategoryAgent" in agent_name:
                        return create_mock_result(
                            {
                                "category": "Meals & Entertainment",
                                "confidence": 0.75,
                                "reasoning": "Team dinner but vendor legitimacy questionable",
                                "vendor_validation": {
                                    "vendor_name": "Joe's Totally Legit Restaurant LLC",
                                    "is_legitimate": False,
                                    "confidence_score": 0.30,
                                    "web_search_summary": "No verified business presence found online",
                                },
                            },
                            ExpenseCategory,
                        )
                    elif "PolicyEvaluationAgent" in agent_name:
                        return create_mock_result(
                            {
                                "compliant": False,
                                "violations": [
                                    {
                                        "rule_name": "VENDOR LEGITIMACY",
                                        "violation_type": "policy_violation",
                                        "severity": "requires_review",
                                        "details": "Vendor cannot be verified as legitimate business",
                                        "threshold_amount": None,
                                    }
                                ],
                                "reasoning": "Vendor legitimacy concerns require human review",
                                "requires_human_review": True,
                                "policy_explanation": "Vendor cannot be verified through web search",
                                "confidence": 0.85,
                            },
                            PolicyEvaluation,
                        )
                    elif "FraudAgent" in agent_name:
                        return create_mock_result(
                            {
                                "overall_risk": "high",
                                "flags": [
                                    {
                                        "flag_type": "suspicious_vendor",
                                        "risk_level": "high",
                                        "details": "Vendor name appears suspicious and cannot be verified",
                                    }
                                ],
                                "reasoning": "High risk due to suspicious vendor name and lack of verification",
                                "requires_human_review": True,
                                "confidence": 0.90,
                                "vendor_risk_indicators": [
                                    "questionable_business_name",
                                    "no_online_verification",
                                ],
                            },
                            FraudAssessment,
                        )
                    elif "DecisionOrchestrationAgent" in agent_name:
                        return create_mock_result(
                            {
                                "decision": "final_rejection",
                                "internal_reasoning": "Vendor legitimacy concerns and fraud indicators make this expense too risky",
                                "external_reasoning": "Expense rejected due to vendor verification issues",
                                "escalation_reason": None,
                                "is_mandatory_escalation": False,
                                "confidence": 0.90,
                            },
                            AgentDecision,
                        )
                    elif "ResponseAgent" in agent_name:
                        return create_mock_result(
                            {
                                "decision_summary": "Your expense has been rejected due to vendor verification issues",
                                "policy_explanation": "All vendors must be verifiable as legitimate businesses",
                                "categorization_summary": "Categorized as Meals & Entertainment but vendor could not be verified",
                            },
                            ExpenseResponse,
                        )
                    else:
                        # Default response
                        class MockRunResult:
                            def __init__(self, final_output):
                                self.final_output = final_output

                        return MockRunResult({"status": "completed"})

                mock_runner.side_effect = get_mock_response

                # Connect to Temporal server
                client = await Client.connect(
                    "localhost:7233", data_converter=open_ai_data_converter
                )

                # Start worker in background with unique task queue
                task_queue = f"{TASK_QUEUE}-test-{uuid.uuid4()}"

                # Initialize ModelActivity for LLM invocation
                model_activity = ModelActivity()

                async with Worker(
                    client,
                    task_queue=task_queue,
                    workflows=[ExpenseWorkflow],
                    activities=[
                        model_activity.invoke_model_activity,
                        create_expense_activity,
                        register_for_decision_activity,
                        payment_activity,
                        update_expense_activity,
                        web_search_activity,
                    ],
                ):
                    # Create suspicious vendor expense
                    expense = ExpenseReport(
                        expense_id="EXP-TEST-003",
                        amount=Decimal("200.00"),
                        description="Team dinner after project completion",
                        vendor="Joe's Totally Legit Restaurant LLC",
                        expense_date=date(2024, 1, 8),
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

                    # Wait for completion with timeout
                    try:
                        result = await asyncio.wait_for(handle.result(), timeout=30.0)

                        # Verify results - should be rejected
                        assert "reject" in result.lower() or "denied" in result.lower()

                        # Check final status
                        status = await handle.query(ExpenseWorkflow.get_status)
                        assert status.current_status in [
                            "final_rejection",
                            "rejected_with_instructions",
                        ]

                    except asyncio.TimeoutError:
                        pytest.fail("Workflow did not complete within 30 seconds")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
