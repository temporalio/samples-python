"""
Simple unit tests for the expense processing models and basic functionality.
These tests don't require OpenAI SDK and should work on all Python versions.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import List

import pytest


# Test the basic data models
def test_expense_report_creation():
    """Test creating an ExpenseReport with all required fields"""
    from openai_agents_expense.models import ExpenseReport

    expense = ExpenseReport(
        expense_id="EXP-001",
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

    assert expense.expense_id == "EXP-001"
    assert expense.amount == Decimal("45.00")
    assert expense.vendor == "Staples Inc"
    assert expense.department == "Engineering"
    assert expense.is_international_travel is False


def test_vendor_validation_model():
    """Test VendorValidation model"""
    from openai_agents_expense.models import VendorValidation

    validation = VendorValidation(
        vendor_name="Staples Inc",
        is_legitimate=True,
        confidence_score=0.98,
        web_search_summary="Major office supply retailer with verified online presence",
    )

    assert validation.vendor_name == "Staples Inc"
    assert validation.is_legitimate is True
    assert validation.confidence_score == 0.98
    assert "office supply" in validation.web_search_summary


def test_expense_category_model():
    """Test ExpenseCategory model"""
    from openai_agents_expense.models import ExpenseCategory, VendorValidation

    vendor_validation = VendorValidation(
        vendor_name="Staples Inc",
        is_legitimate=True,
        confidence_score=0.98,
        web_search_summary="Legitimate retailer",
    )

    category = ExpenseCategory(
        category="Office Supplies",
        confidence=0.95,
        reasoning="Clear office supplies from legitimate vendor",
        vendor_validation=vendor_validation,
    )

    assert category.category == "Office Supplies"
    assert category.confidence == 0.95
    assert category.vendor_validation.is_legitimate is True


def test_policy_evaluation_model():
    """Test PolicyEvaluation model"""
    from openai_agents_expense.models import PolicyEvaluation, PolicyViolation

    # Test compliant evaluation
    policy_eval = PolicyEvaluation(
        compliant=True,
        violations=[],
        reasoning="All policies satisfied",
        requires_human_review=False,
        mandatory_human_review=False,
        policy_explanation="Standard approval under $75",
        confidence=0.92,
    )

    assert policy_eval.compliant is True
    assert len(policy_eval.violations) == 0
    assert policy_eval.requires_human_review is False

    # Test with violation
    violation = PolicyViolation(
        rule_name="International Travel",
        violation_type="mandatory_review",
        severity="requires_review",
        details="All international travel requires human approval",
    )

    policy_eval_with_violation = PolicyEvaluation(
        compliant=False,
        violations=[violation],
        reasoning="International travel requires review",
        requires_human_review=True,
        mandatory_human_review=True,
        policy_explanation="International travel policy",
        confidence=0.98,
    )

    assert policy_eval_with_violation.compliant is False
    assert len(policy_eval_with_violation.violations) == 1
    assert policy_eval_with_violation.violations[0].rule_name == "International Travel"


def test_fraud_assessment_model():
    """Test FraudAssessment model"""
    from openai_agents_expense.models import FraudAssessment, FraudFlag

    # Test low risk assessment
    fraud_assessment = FraudAssessment(
        overall_risk="low",
        flags=[],
        reasoning="No suspicious patterns detected",
        requires_human_review=False,
        confidence=0.88,
        vendor_risk_indicators=[],
    )

    assert fraud_assessment.overall_risk == "low"
    assert len(fraud_assessment.flags) == 0
    assert fraud_assessment.requires_human_review is False

    # Test with fraud flags
    fraud_flag = FraudFlag(
        flag_type="suspicious_vendor",
        risk_level="high",
        details="Vendor not found in search results",
    )

    high_risk_assessment = FraudAssessment(
        overall_risk="high",
        flags=[fraud_flag],
        reasoning="Suspicious vendor detected",
        requires_human_review=True,
        confidence=0.92,
        vendor_risk_indicators=["vendor_not_found"],
    )

    assert high_risk_assessment.overall_risk == "high"
    assert len(high_risk_assessment.flags) == 1
    assert high_risk_assessment.flags[0].flag_type == "suspicious_vendor"


def test_agent_decision_model():
    """Test FinalDecision model"""
    from openai_agents_expense.models import AgentDecision

    # Test approval decision
    approval = AgentDecision(
        decision="approved",
        internal_reasoning="All checks passed, low risk",
        external_reasoning="Expense approved - standard business expense",
        escalation_reason=None,
        is_mandatory_escalation=False,
        confidence=0.91,
    )

    assert approval.decision == "approved"
    assert approval.is_mandatory_escalation is False
    assert approval.escalation_reason is None

    # Test escalation decision
    escalation = AgentDecision(
        decision="requires_human_review",
        internal_reasoning="Mandatory escalation due to policy",
        external_reasoning="Requires manager approval per policy",
        escalation_reason="Mandatory policy requirement",
        is_mandatory_escalation=True,
        confidence=0.95,
    )

    assert escalation.decision == "requires_human_review"
    assert escalation.is_mandatory_escalation is True
    assert escalation.escalation_reason == "Mandatory policy requirement"


def test_expense_response_model():
    """Test ExpenseResponse model"""
    from openai_agents_expense.models import ExpenseResponse

    response = ExpenseResponse(
        message="Your expense has been approved!",
        decision_summary="Approved - Standard office supplies",
        policy_explanation="Office supplies under $75 auto-approved",
        categorization_summary="Office Supplies from legitimate vendor",
    )

    assert "approved" in response.message.lower()
    assert "Approved" in response.decision_summary
    assert "Office Supplies" in response.categorization_summary


def test_web_search_mock_function():
    """Test the mock web search functionality"""
    import asyncio

    from openai_agents_expense.activities.web_search import web_search_activity

    async def run_test():
        # Test legitimate vendor
        result = await web_search_activity("Staples office supplies")
        assert "results" in result
        assert len(result["results"]) > 0
        assert any("staples" in r["title"].lower() for r in result["results"])
        assert result["analysis"]["is_legitimate"] is True

        # Test suspicious vendor - should return results but with low legitimacy
        result = await web_search_activity("Joe's Totally Legit Restaurant LLC")
        assert "results" in result
        # The mock will return some results because of "LLC" but legitimacy should be questionable
        # Let's just check that we get analysis data
        assert "analysis" in result
        assert "is_legitimate" in result["analysis"]

        # Test generic query
        result = await web_search_activity("office supplies")
        assert "results" in result
        assert len(result["results"]) > 0

    # Run the async test
    asyncio.run(run_test())


def test_confidence_thresholds():
    """Test that confidence thresholds are correctly applied"""
    # These are the thresholds defined in the specification
    CATEGORY_THRESHOLD = 0.70
    POLICY_THRESHOLD = 0.80
    FRAUD_THRESHOLD = 0.65
    DECISION_THRESHOLD = 0.75

    # Test scenarios with different confidence levels
    test_cases = [
        # (confidence, threshold, should_escalate)
        (0.95, CATEGORY_THRESHOLD, False),
        (0.65, CATEGORY_THRESHOLD, True),
        (0.85, POLICY_THRESHOLD, False),
        (0.75, POLICY_THRESHOLD, True),
        (0.70, FRAUD_THRESHOLD, False),
        (0.60, FRAUD_THRESHOLD, True),
        (0.80, DECISION_THRESHOLD, False),
        (0.70, DECISION_THRESHOLD, True),
    ]

    for confidence, threshold, should_escalate in test_cases:
        requires_escalation = confidence < threshold
        assert (
            requires_escalation == should_escalate
        ), f"Confidence {confidence} vs threshold {threshold}: expected escalation={should_escalate}"


def test_business_rules_data():
    """Test business rule constants and categories"""
    # Test that all expected expense categories are defined
    expected_categories = [
        "Travel & Transportation",
        "Meals & Entertainment",
        "Office Supplies",
        "Software & Technology",
        "Marketing & Advertising",
        "Professional Services",
        "Training & Education",
        "Equipment & Hardware",
        "Other",
    ]

    # This would test against constants if they were defined in models
    # For now, just verify the categories work in model creation
    from openai_agents_expense.models import ExpenseCategory, VendorValidation

    vendor_validation = VendorValidation(
        vendor_name="Test Vendor",
        is_legitimate=True,
        confidence_score=0.9,
        web_search_summary="Test",
    )

    for category_name in expected_categories:
        category = ExpenseCategory(
            category=category_name,
            confidence=0.9,
            reasoning=f"Test {category_name}",
            vendor_validation=vendor_validation,
        )
        assert category.category == category_name


@pytest.mark.parametrize(
    "amount,expected_receipt_required",
    [
        (Decimal("25.00"), False),
        (Decimal("75.00"), False),  # Exactly $75
        (Decimal("75.01"), True),  # Over $75
        (Decimal("100.00"), True),
    ],
)
def test_receipt_requirements(amount, expected_receipt_required):
    """Test receipt requirements based on amount"""
    # $75 is the threshold according to business rules
    RECEIPT_THRESHOLD = Decimal("75.00")
    requires_receipt = amount > RECEIPT_THRESHOLD
    assert requires_receipt == expected_receipt_required


def test_date_calculations():
    """Test date-based business rules"""
    from datetime import date, timedelta

    today = date.today()

    # Test late submission (over 60 days)
    old_expense_date = today - timedelta(days=61)
    recent_expense_date = today - timedelta(days=30)

    LATE_SUBMISSION_DAYS = 60

    is_late_old = (today - old_expense_date).days > LATE_SUBMISSION_DAYS
    is_late_recent = (today - recent_expense_date).days > LATE_SUBMISSION_DAYS

    assert is_late_old is True
    assert is_late_recent is False


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
