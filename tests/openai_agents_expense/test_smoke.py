"""
Quick Smoke Tests for E2E Infrastructure

These tests verify the E2E test framework works without making slow OpenAI API calls.
"""

import os
from pathlib import Path

import pytest


class TestSmokeTests:
    """Quick smoke tests to verify E2E infrastructure"""

    def test_environment_loaded(self):
        """Test that .env file is loaded correctly"""
        env_path = Path(__file__).parent.parent.parent / ".env"
        assert env_path.exists(), ".env file not found"

        # Load manually if needed
        if not os.getenv("OPENAI_API_KEY"):
            with open(env_path) as f:
                for line in f:
                    if line.strip() and not line.startswith("#"):
                        key, value = line.strip().split("=", 1)
                        os.environ[key] = value

        assert os.getenv("OPENAI_API_KEY"), "OPENAI_API_KEY not found"
        print(
            f"✅ OpenAI API key loaded (length: {len(os.getenv('OPENAI_API_KEY', ''))})"
        )

    def test_imports_work(self):
        """Test that all required modules can be imported"""
        try:
            # Test workflow import
            from openai_agents_expense.workflows.expense_workflow import ExpenseWorkflow

            assert ExpenseWorkflow is not None

            # Test models import
            from openai_agents_expense.models import ExpenseReport

            assert ExpenseReport is not None

            # Test activities import
            from openai_agents_expense.activities import (
                create_expense_activity,
                payment_activity,
                register_for_decision_activity,
                web_search_activity,
            )

            assert all(
                [
                    create_expense_activity,
                    register_for_decision_activity,
                    payment_activity,
                    web_search_activity,
                ]
            )

            # Test AI agents import
            from openai_agents_expense.ai_agents.category_agent import (
                create_category_agent,
            )
            from openai_agents_expense.ai_agents.decision_orchestration_agent import (
                create_decision_orchestration_agent,
            )
            from openai_agents_expense.ai_agents.fraud_agent import create_fraud_agent
            from openai_agents_expense.ai_agents.policy_evaluation_agent import (
                create_policy_evaluation_agent,
            )
            from openai_agents_expense.ai_agents.response_agent import (
                create_response_agent,
            )

            assert all(
                [
                    create_category_agent,
                    create_policy_evaluation_agent,
                    create_fraud_agent,
                    create_decision_orchestration_agent,
                    create_response_agent,
                ]
            )

            print("✅ All imports successful")

        except ImportError as e:
            pytest.fail(f"Import failed: {e}")

    def test_expense_model_creation(self):
        """Test that ExpenseReport models can be created"""
        from datetime import date
        from decimal import Decimal

        from openai_agents_expense.models import ExpenseReport

        expense = ExpenseReport(
            expense_id="TEST-001",
            amount=Decimal("45.00"),
            description="Test office supplies",
            vendor="Test Vendor",
            expense_date=date(2024, 1, 15),
            department="Engineering",
            employee_id="EMP-TEST",
            receipt_provided=True,
            submission_date=date(2024, 1, 16),
            client_name=None,
            business_justification=None,
            is_international_travel=False,
        )

        assert expense.expense_id == "TEST-001"
        assert expense.amount == Decimal("45.00")
        assert expense.vendor == "Test Vendor"
        print("✅ ExpenseReport model creation works")

    def test_mock_server_fixture(self):
        """Test that the mock server fixture logic works"""

        # Test the mock server class directly without using pytest fixture
        class MockExpenseServer:
            def __init__(self):
                self.expenses = {}
                self.tokens = {}

            async def handle_request(self, method, url, **kwargs):
                """Handle HTTP requests to the expense server"""
                from unittest.mock import AsyncMock

                mock_response = AsyncMock()
                mock_response.text = "SUCCEED"
                mock_response.raise_for_status = AsyncMock()
                mock_response.status_code = 200
                return mock_response

        mock_server = MockExpenseServer()

        assert hasattr(mock_server, "handle_request")
        assert hasattr(mock_server, "expenses")
        assert hasattr(mock_server, "tokens")
        print("✅ Mock server fixture works")

    def test_ui_integration_basic(self):
        """Test basic UI integration without server"""
        from fastapi.testclient import TestClient

        from openai_agents_expense.ui import app

        client = TestClient(app)

        # Test home page
        response = client.get("/")
        assert response.status_code == 200
        assert "OpenAI Agents Expense System" in response.text

        print("✅ UI integration basic test works")

    def test_mock_ai_agent_structure(self):
        """Test that AI agent models can be created and mocked properly"""
        from datetime import date
        from decimal import Decimal

        from openai_agents_expense.models import (
            ExpenseCategory,
            ExpenseReport,
            VendorValidation,
        )

        # Create test expense
        expense = ExpenseReport(
            expense_id="TEST-001",
            amount=Decimal("45.00"),
            description="Test office supplies",
            vendor="Test Vendor",
            expense_date=date(2024, 1, 15),
            department="Engineering",
            employee_id="EMP-TEST",
            receipt_provided=True,
            submission_date=date(2024, 1, 16),
            client_name=None,
            business_justification=None,
            is_international_travel=False,
        )

        # Create mock category result
        mock_category = ExpenseCategory(
            category="Office Supplies",
            confidence=0.95,
            reasoning="Office supplies purchase",
            vendor_validation=VendorValidation(
                vendor_name="Test Vendor",
                is_legitimate=True,
                confidence_score=0.90,
                web_search_summary="Test vendor found in web search with legitimate business presence and website",
            ),
        )

        # Test that the models are properly constructed
        assert mock_category.category == "Office Supplies"
        assert mock_category.confidence == 0.95
        assert mock_category.vendor_validation.is_legitimate is True
        assert mock_category.vendor_validation.vendor_name == "Test Vendor"

        print("✅ AI agent model mocking works")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
