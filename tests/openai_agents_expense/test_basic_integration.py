"""
Basic integration tests to verify imports and structure work correctly.
"""

from datetime import date
from decimal import Decimal

import pytest


def test_basic_imports():
    """Test that all main components can be imported successfully"""

    # Test workflow import
    try:
        from openai_agents_expense.workflows.expense_workflow import ExpenseWorkflow

        assert ExpenseWorkflow is not None
        assert hasattr(ExpenseWorkflow, "run")
    except ImportError as e:
        pytest.fail(f"Could not import ExpenseWorkflow: {e}")

    # Test model imports
    try:
        from openai_agents_expense.models import (
            AgentDecision,
            ExpenseCategory,
            ExpenseProcessingData,
            ExpenseReport,
            ExpenseResponse,
            ExpenseStatus,
            FraudAssessment,
            PolicyEvaluation,
            VendorValidation,
        )

        assert all(
            [
                ExpenseReport,
                ExpenseCategory,
                VendorValidation,
                PolicyEvaluation,
                FraudAssessment,
                AgentDecision,
                ExpenseResponse,
                ExpenseStatus,
                ExpenseProcessingData,
            ]
        )
    except ImportError as e:
        pytest.fail(f"Could not import models: {e}")

    # Test AI agent creator function imports
    try:
        from openai_agents_expense.ai_agents.category_agent import create_category_agent
        from openai_agents_expense.ai_agents.decision_orchestration_agent import (
            create_decision_orchestration_agent,
        )
        from openai_agents_expense.ai_agents.fraud_agent import create_fraud_agent
        from openai_agents_expense.ai_agents.policy_evaluation_agent import (
            create_policy_evaluation_agent,
        )
        from openai_agents_expense.ai_agents.response_agent import create_response_agent

        assert all(
            [
                create_category_agent,
                create_policy_evaluation_agent,
                create_fraud_agent,
                create_decision_orchestration_agent,
                create_response_agent,
            ]
        )
    except ImportError as e:
        pytest.fail(f"Could not import AI agent creator functions: {e}")

    # Test activity imports
    try:
        from openai_agents_expense.activities.web_search import web_search_activity

        assert web_search_activity is not None
    except ImportError as e:
        pytest.fail(f"Could not import activities: {e}")


def test_expense_report_creation():
    """Test creating an ExpenseReport with all logging-relevant fields"""
    from openai_agents_expense.models import ExpenseReport

    expense = ExpenseReport(
        expense_id="TEST-001",
        amount=Decimal("125.50"),
        description="Test expense for logging verification",
        vendor="Test Vendor LLC",
        expense_date=date.today(),
        department="Engineering",
        employee_id="EMP-TEST",
        receipt_provided=True,
        submission_date=date.today(),
        client_name="Test Client",
        business_justification="Testing logging functionality",
        is_international_travel=False,
    )

    # Verify all fields used in logging are accessible
    assert expense.expense_id == "TEST-001"
    assert expense.amount == Decimal("125.50")
    assert expense.vendor == "Test Vendor LLC"
    assert expense.description == "Test expense for logging verification"
    assert expense.department == "Engineering"
    assert expense.employee_id == "EMP-TEST"
    assert expense.is_international_travel is False
    assert expense.receipt_provided is True


def test_workflow_structure():
    """Test that the workflow has the expected structure for logging"""
    from openai_agents_expense.workflows.expense_workflow import ExpenseWorkflow

    # Verify workflow has required methods
    assert hasattr(ExpenseWorkflow, "run")
    assert hasattr(ExpenseWorkflow, "get_status")
    assert hasattr(ExpenseWorkflow, "get_processing_result")

    # Verify the workflow class is properly defined
    assert ExpenseWorkflow.__name__ == "ExpenseWorkflow"
    assert callable(ExpenseWorkflow.run)
    assert callable(ExpenseWorkflow.get_status)
    assert callable(ExpenseWorkflow.get_processing_result)


@pytest.mark.asyncio
async def test_web_search_activity():
    """Test web search activity works for logging verification"""
    from openai_agents_expense.activities.web_search import web_search_activity

    # Test with a simple query that should return results
    result = await web_search_activity("office supplies")

    # Verify structure expected by logging
    assert "query" in result
    assert "results" in result
    assert "analysis" in result
    assert "result_count" in result

    analysis = result["analysis"]
    assert "is_legitimate" in analysis
    assert "confidence_score" in analysis
    assert "business_type" in analysis
    assert "legitimacy_indicators" in analysis


def test_ai_agent_creator_functions():
    """Test that AI agent creator functions work correctly"""
    from openai_agents_expense.ai_agents.category_agent import create_category_agent
    from openai_agents_expense.ai_agents.decision_orchestration_agent import (
        create_decision_orchestration_agent,
    )
    from openai_agents_expense.ai_agents.fraud_agent import create_fraud_agent
    from openai_agents_expense.ai_agents.policy_evaluation_agent import (
        create_policy_evaluation_agent,
    )
    from openai_agents_expense.ai_agents.response_agent import create_response_agent

    # Test that creator functions return Agent objects and are callable
    category_agent = create_category_agent()
    policy_agent = create_policy_evaluation_agent()
    fraud_agent = create_fraud_agent()
    decision_agent = create_decision_orchestration_agent()
    response_agent = create_response_agent()

    # Verify all agents have the expected attributes
    for agent in [
        category_agent,
        policy_agent,
        fraud_agent,
        decision_agent,
        response_agent,
    ]:
        assert hasattr(agent, "name")
        assert hasattr(agent, "instructions")
        assert hasattr(agent, "output_type")

    # Verify specific agent names
    assert category_agent.name == "CategoryAgent"
    assert policy_agent.name == "PolicyEvaluationAgent"
    assert fraud_agent.name == "FraudAgent"
    assert decision_agent.name == "DecisionOrchestrationAgent"
    assert response_agent.name == "ResponseAgent"


if __name__ == "__main__":
    # Run basic smoke test if called directly
    test_basic_imports()
    test_expense_report_creation()
    test_workflow_structure()
    print("✅ All basic integration tests passed!")
