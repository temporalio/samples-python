"""
Simplified unit tests for OpenAI Agents Expense Processing.

These tests focus on verifying that the self-contained functionality works:
- All imports work correctly
- Basic function signatures are correct
- Core workflow components are accessible
"""

from datetime import date
from decimal import Decimal

import pytest


class TestAgentImports:
    """Test that all AI agent functions can be imported correctly"""

    def test_category_agent_imports(self):
        """Test CategoryAgent components can be imported"""
        from openai_agents_expense.ai_agents.category_agent import (
            categorize_expense,
            create_category_agent,
        )

        # Verify functions exist and are callable
        assert callable(categorize_expense)
        assert callable(create_category_agent)

    def test_policy_evaluation_agent_imports(self):
        """Test PolicyEvaluationAgent components can be imported"""
        from openai_agents_expense.ai_agents.policy_evaluation_agent import (
            evaluate_policy_compliance,
        )

        assert callable(evaluate_policy_compliance)

    def test_fraud_agent_imports(self):
        """Test FraudAgent components can be imported"""
        from openai_agents_expense.ai_agents.fraud_agent import assess_fraud_risk

        assert callable(assess_fraud_risk)

    def test_decision_orchestration_agent_imports(self):
        """Test DecisionOrchestrationAgent components can be imported"""
        from openai_agents_expense.ai_agents.decision_orchestration_agent import (
            make_agent_decision,
        )

        assert callable(make_agent_decision)

    def test_response_agent_imports(self):
        """Test ResponseAgent components can be imported"""
        from openai_agents_expense.ai_agents.response_agent import (
            generate_expense_response,
        )

        assert callable(generate_expense_response)

    def test_all_agents_via_package_import(self):
        """Test all agent functions can be imported via the package"""
        from openai_agents_expense.ai_agents import (
            assess_fraud_risk,
            categorize_expense,
            evaluate_policy_compliance,
            generate_expense_response,
            make_agent_decision,
        )

        # Verify all functions are callable
        assert callable(categorize_expense)
        assert callable(evaluate_policy_compliance)
        assert callable(assess_fraud_risk)
        assert callable(make_agent_decision)
        assert callable(generate_expense_response)


class TestAgentCreation:
    """Test that OpenAI Agent instances can be created"""

    def test_create_category_agent(self):
        """Test that CategoryAgent can be created"""
        from openai_agents_expense.ai_agents.category_agent import create_category_agent

        agent = create_category_agent()

        # Verify it's an Agent instance
        assert hasattr(agent, "name")
        assert hasattr(agent, "instructions")
        assert hasattr(agent, "tools")
        assert agent.name == "CategoryAgent"

    def test_create_policy_evaluation_agent(self):
        """Test that PolicyEvaluationAgent can be created"""
        from openai_agents_expense.ai_agents.policy_evaluation_agent import (
            create_policy_evaluation_agent,
        )

        agent = create_policy_evaluation_agent()

        assert hasattr(agent, "name")
        assert agent.name == "PolicyEvaluationAgent"

    def test_create_fraud_agent(self):
        """Test that FraudAgent can be created"""
        from openai_agents_expense.ai_agents.fraud_agent import create_fraud_agent

        agent = create_fraud_agent()

        assert hasattr(agent, "name")
        assert agent.name == "FraudAgent"

    def test_create_decision_orchestration_agent(self):
        """Test that DecisionOrchestrationAgent can be created"""
        from openai_agents_expense.ai_agents.decision_orchestration_agent import (
            create_decision_orchestration_agent,
        )

        agent = create_decision_orchestration_agent()

        assert hasattr(agent, "name")
        assert agent.name == "DecisionOrchestrationAgent"

    def test_create_response_agent(self):
        """Test that ResponseAgent can be created"""
        from openai_agents_expense.ai_agents.response_agent import create_response_agent

        agent = create_response_agent()

        assert hasattr(agent, "name")
        assert agent.name == "ResponseAgent"


class TestModelsIntegration:
    """Test that models integrate correctly with agent functions"""

    def test_expense_report_creation(self):
        """Test ExpenseReport model can be created"""
        from openai_agents_expense.models import ExpenseReport

        expense = ExpenseReport(
            expense_id="TEST-001",
            amount=Decimal("45.00"),
            description="Test expense",
            vendor="Test Vendor",
            date=date.today(),
            department="Engineering",
            employee_id="EMP-123",
            receipt_provided=True,
            submission_date=date.today(),
            client_name=None,
            business_justification=None,
            is_international_travel=False,
        )

        assert expense.expense_id == "TEST-001"
        assert expense.amount == Decimal("45.00")
        assert expense.vendor == "Test Vendor"

    def test_all_model_imports(self):
        """Test all required models can be imported"""
        from openai_agents_expense.models import (
            AgentDecision,
            ExpenseCategory,
            ExpenseProcessingData,
            ExpenseReport,
            ExpenseResponse,
            ExpenseStatus,
            FraudAssessment,
            FraudFlag,
            PolicyEvaluation,
            PolicyViolation,
            VendorValidation,
        )

        # Verify all models are classes
        assert isinstance(ExpenseReport, type)
        assert isinstance(ExpenseCategory, type)
        assert isinstance(VendorValidation, type)
        assert isinstance(PolicyEvaluation, type)
        assert isinstance(PolicyViolation, type)
        assert isinstance(FraudAssessment, type)
        assert isinstance(FraudFlag, type)
        assert isinstance(AgentDecision, type)
        assert isinstance(ExpenseResponse, type)
        assert isinstance(ExpenseProcessingData, type)
        assert isinstance(ExpenseStatus, type)


class TestActivitiesIntegration:
    """Test that activities integrate correctly"""

    def test_expense_activities_import(self):
        """Test expense activities can be imported"""
        from openai_agents_expense.activities import (
            create_expense_activity,
            payment_activity,
            wait_for_decision_activity,
            web_search_activity,
        )

        # Verify activities are callable
        assert callable(create_expense_activity)
        assert callable(wait_for_decision_activity)
        assert callable(payment_activity)
        assert callable(web_search_activity)

    def test_web_search_activity_import(self):
        """Test web search activity can be imported directly"""
        from openai_agents_expense.activities.web_search import web_search_activity

        assert callable(web_search_activity)


class TestWorkflowIntegration:
    """Test that workflow components integrate correctly"""

    def test_expense_workflow_import(self):
        """Test ExpenseWorkflow can be imported"""
        from openai_agents_expense.workflows.expense_workflow import ExpenseWorkflow

        # Verify it's a workflow class
        assert hasattr(ExpenseWorkflow, "run")
        assert callable(ExpenseWorkflow.run)

    def test_workflow_queries_exist(self):
        """Test workflow query methods exist"""
        from openai_agents_expense.workflows.expense_workflow import ExpenseWorkflow

        # Verify query methods exist
        assert hasattr(ExpenseWorkflow, "get_status")
        assert hasattr(ExpenseWorkflow, "get_processing_result")


class TestUIIntegration:
    """Test that UI components work correctly"""

    def test_ui_imports(self):
        """Test UI components can be imported"""
        from openai_agents_expense.ui import ExpenseReviewState, main

        assert callable(main)
        assert hasattr(ExpenseReviewState, "CREATED")
        assert hasattr(ExpenseReviewState, "APPROVED")
        assert hasattr(ExpenseReviewState, "REJECTED")
        assert hasattr(ExpenseReviewState, "COMPLETED")


class TestSelfContainedConfiguration:
    """Test that the self-contained configuration is correct"""

    def test_package_constants(self):
        """Test package constants are accessible"""
        from openai_agents_expense import (
            EXPENSE_SERVER_HOST_PORT,
            TASK_QUEUE,
            WORKFLOW_ID_PREFIX,
        )

        assert isinstance(EXPENSE_SERVER_HOST_PORT, str)
        assert isinstance(TASK_QUEUE, str)
        assert isinstance(WORKFLOW_ID_PREFIX, str)

        # Verify values make sense
        assert "http://" in EXPENSE_SERVER_HOST_PORT
        assert "openai-agents-expense" in TASK_QUEUE
        assert "openai-agents-expense" in WORKFLOW_ID_PREFIX

    def test_worker_imports(self):
        """Test worker can import all required components"""
        from openai_agents_expense.worker import main

        assert callable(main)

    def test_starter_imports(self):
        """Test starter can import all required components"""
        from openai_agents_expense.starter import main

        assert callable(main)


# Mark all tests as unit tests
pytestmark = pytest.mark.unit
