"""Pytest configuration for OpenAI Agents Expense Processing tests"""

import os
import sys
from datetime import date
from decimal import Decimal

import pytest

# Add the parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
async def client():
    """Create a Temporal client for testing"""
    # Only import temporal if we're running integration tests
    try:
        from temporalio.testing import WorkflowEnvironment

        async with WorkflowEnvironment.start_time_skipping() as env:
            yield env.client
    except ImportError:
        # Skip if temporal is not available
        pytest.skip("Temporal testing environment not available")


@pytest.fixture
def sample_expense_report():
    """Create a sample expense report for testing"""
    try:
        from openai_agents_expense.models import ExpenseReport

        return ExpenseReport(
            expense_id="EXP-TEST-001",
            amount=Decimal("45.00"),
            description="Office supplies - pens, paper, folders",
            vendor="Staples Inc",
            date=date.today(),
            department="Engineering",
            employee_id="EMP-123",
            receipt_provided=True,
            submission_date=date.today(),
            client_name=None,
            business_justification=None,
            is_international_travel=False,
        )
    except ImportError:
        pytest.skip("Models not available")


@pytest.fixture
def international_travel_expense():
    """Create an international travel expense for testing"""
    from openai_agents_expense.models import ExpenseReport

    return ExpenseReport(
        expense_id="EXP-TEST-002",
        amount=Decimal("400.00"),
        description="Flight to London for business meeting",
        vendor="British Airways",
        date=date.today(),
        department="Sales",
        employee_id="EMP-456",
        receipt_provided=True,
        submission_date=date.today(),
        client_name=None,
        business_justification=None,
        is_international_travel=True,
    )


@pytest.fixture
def suspicious_vendor_expense():
    """Create an expense with suspicious vendor for testing"""
    from openai_agents_expense.models import ExpenseReport

    return ExpenseReport(
        expense_id="EXP-TEST-003",
        amount=Decimal("200.00"),
        description="Business meal with client",
        vendor="Joe's Totally Legit Restaurant LLC",
        date=date.today(),
        department="Marketing",
        employee_id="EMP-789",
        receipt_provided=True,
        submission_date=date.today(),
        client_name="John Smith Corp",
        business_justification="Quarterly business review meeting",
        is_international_travel=False,
    )


@pytest.fixture
def sample_vendor_validation():
    """Create sample vendor validation for testing"""
    from openai_agents_expense.models import VendorValidation

    return VendorValidation(
        vendor_name="Staples Inc",
        is_legitimate=True,
        confidence_score=0.98,
        web_search_summary="Staples Inc. is a major office supply chain with website at staples.com, extensive store network, and legitimate business operations.",
    )


@pytest.fixture
def sample_expense_category(sample_vendor_validation):
    """Create sample expense category for testing"""
    from openai_agents_expense.models import ExpenseCategory

    return ExpenseCategory(
        category="Office Supplies",
        confidence=0.95,
        reasoning="Clear office supplies from legitimate vendor Staples Inc.",
        vendor_validation=sample_vendor_validation,
    )


@pytest.fixture
def compliant_policy_evaluation():
    """Create compliant policy evaluation for testing"""
    from openai_agents_expense.models import PolicyEvaluation

    return PolicyEvaluation(
        compliant=True,
        violations=[],
        reasoning="Office supplies expense under $75, fully compliant with all policies",
        requires_human_review=False,
        mandatory_human_review=False,
        policy_explanation="Office supplies under $75 are automatically approved when from legitimate vendors",
        confidence=0.92,
    )


@pytest.fixture
def low_risk_fraud_assessment():
    """Create low risk fraud assessment for testing"""
    from openai_agents_expense.models import FraudAssessment

    return FraudAssessment(
        overall_risk="low",
        flags=[],
        reasoning="Low fraud risk - legitimate vendor, reasonable amount for category, no suspicious patterns detected",
        requires_human_review=False,
        confidence=0.88,
        vendor_risk_indicators=[],
    )


@pytest.fixture
def approval_decision():
    """Create approval decision for testing"""
    from openai_agents_expense.models import AgentDecision

    return AgentDecision(
        decision="approved",
        internal_reasoning="Clear case for approval: high confidence categorization, policy compliant, low fraud risk, all thresholds exceeded",
        external_reasoning="Expense approved: Office supplies from legitimate vendor, compliant with company policies, standard business expense",
        escalation_reason=None,
        is_mandatory_escalation=False,
        confidence=0.91,
    )


# Configure pytest markers
def pytest_configure(config):
    """Configure custom pytest markers"""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "openai: mark test as requiring OpenAI mocking")


# Skip OpenAI tests on older Python versions
def pytest_collection_modifyitems(config, items):
    """Modify test collection to skip OpenAI tests on Python < 3.11"""
    if sys.version_info < (3, 11):
        skip_openai = pytest.mark.skip(
            reason="OpenAI support has type errors on Python < 3.11"
        )
        for item in items:
            if "openai" in item.keywords:
                item.add_marker(skip_openai)
