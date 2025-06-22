"""
Basic integration tests to verify imports and structure work correctly.
"""

import pytest
import sys
from decimal import Decimal
from datetime import date


def test_basic_imports():
    """Test that all main components can be imported successfully"""
    
    # Test workflow import
    try:
        from openai_agents_expense.workflows.expense_workflow import ExpenseWorkflow
        assert ExpenseWorkflow is not None
        assert hasattr(ExpenseWorkflow, 'run')
    except ImportError as e:
        pytest.fail(f"Could not import ExpenseWorkflow: {e}")
    
    # Test model imports  
    try:
        from openai_agents_expense.models import (
            ExpenseReport, ExpenseCategory, VendorValidation,
            PolicyEvaluation, FraudAssessment, FinalDecision,
            ExpenseResponse, ExpenseStatus, ExpenseProcessingResult
        )
        assert all([
            ExpenseReport, ExpenseCategory, VendorValidation,
            PolicyEvaluation, FraudAssessment, FinalDecision,
            ExpenseResponse, ExpenseStatus, ExpenseProcessingResult
        ])
    except ImportError as e:
        pytest.fail(f"Could not import models: {e}")
    
    # Test AI agent function imports
    try:
        from openai_agents_expense.ai_agents.category_agent import categorize_expense
        from openai_agents_expense.ai_agents.policy_evaluation_agent import evaluate_policy_compliance
        from openai_agents_expense.ai_agents.fraud_agent import assess_fraud_risk
        from openai_agents_expense.ai_agents.decision_orchestration_agent import make_final_decision
        from openai_agents_expense.ai_agents.response_agent import generate_expense_response
        
        assert all([
            categorize_expense, evaluate_policy_compliance, assess_fraud_risk,
            make_final_decision, generate_expense_response
        ])
    except ImportError as e:
        pytest.fail(f"Could not import AI agent functions: {e}")
    
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
        date=date.today(),
        department="Engineering",
        employee_id="EMP-TEST",
        receipt_provided=True,
        submission_date=date.today(),
        client_name="Test Client",
        business_justification="Testing logging functionality",
        is_international_travel=False
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
    assert hasattr(ExpenseWorkflow, 'run')
    assert hasattr(ExpenseWorkflow, 'get_status')
    assert hasattr(ExpenseWorkflow, 'get_processing_result')
    
    # Verify the workflow class is properly defined
    assert ExpenseWorkflow.__name__ == 'ExpenseWorkflow'
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


def test_ai_agent_function_signatures():
    """Test that AI agent functions have expected signatures for logging"""
    from openai_agents_expense.ai_agents.category_agent import categorize_expense
    from openai_agents_expense.ai_agents.policy_evaluation_agent import evaluate_policy_compliance
    from openai_agents_expense.ai_agents.fraud_agent import assess_fraud_risk
    from openai_agents_expense.ai_agents.decision_orchestration_agent import make_final_decision
    from openai_agents_expense.ai_agents.response_agent import generate_expense_response
    
    # Just verify functions are callable (they're async so we can't easily test return values)
    import inspect
    
    assert inspect.iscoroutinefunction(categorize_expense)
    assert inspect.iscoroutinefunction(evaluate_policy_compliance)
    assert inspect.iscoroutinefunction(assess_fraud_risk)
    assert inspect.iscoroutinefunction(make_final_decision)
    assert inspect.iscoroutinefunction(generate_expense_response)
    
    # Check expected parameter counts
    assert len(inspect.signature(categorize_expense).parameters) == 1  # expense_report
    assert len(inspect.signature(evaluate_policy_compliance).parameters) == 2  # expense_report, categorization
    assert len(inspect.signature(assess_fraud_risk).parameters) == 2  # expense_report, categorization 
    assert len(inspect.signature(make_final_decision).parameters) == 4  # expense_report, categorization, policy_eval, fraud_assessment
    assert len(inspect.signature(generate_expense_response).parameters) == 4  # expense_report, categorization, policy_eval, final_decision


if __name__ == "__main__":
    # Run basic smoke test if called directly
    test_basic_imports()
    test_expense_report_creation()
    test_workflow_structure()
    print("✅ All basic integration tests passed!") 