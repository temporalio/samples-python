"""
DecisionOrchestrationAgent - Make final approval decisions using all available context.

This agent is responsible for:
1. Making final approval decisions using all available context
2. Respecting mandatory escalation rules that override AI assessment
3. Combining policy evaluation and fraud assessment with confidence scores
4. Information Access: Private - sees all context but only outputs sanitized decisions
"""

from temporalio import workflow

# Import models at module level for consistent type identity
from openai_agents_expense.models import (
    AgentDecision,
    ExpenseCategory,
    ExpenseReport,
    FraudAssessment,
    PolicyEvaluation,
)

# Import agent components and models
with workflow.unsafe.imports_passed_through():
    from agents import Agent


def create_decision_orchestration_agent() -> Agent:
    """
    Create the DecisionOrchestrationAgent for final decision making.

    Returns:
        Configured Agent instance for decision orchestration
    """
    instructions = """
    You are a decision orchestration specialist responsible for making final expense approval decisions by combining multiple assessment inputs.

    DECISION TYPES (must choose exactly one):
    1. "approved" - Clear cases with high confidence and policy compliance
    2. "final_rejection" - Clear policy violations with no exceptions allowed
    3. "requires_human_review" - Serious issues requiring investigation (fraud suspicion, high-stakes ambiguity, policy exceptions)
    4. "rejected_with_instructions" - Fixable issues where employee can provide clarification and resubmit

    MANDATORY ESCALATION RULES (override AI assessment):
    These ALWAYS result in "requires_human_review" regardless of other factors:
    - International travel (regardless of AI assessment)
    - Flight expenses over $500 (regardless of AI assessment)  
    - Equipment/hardware over $250 (regardless of AI assessment)
    - Late submissions over 60 days (regardless of AI assessment)

    CONFIDENCE THRESHOLDS FOR AI-DRIVEN ESCALATION:
    - CategoryAgent: < 0.70 (foundational errors cascade downstream)
    - PolicyEvaluationAgent: < 0.80 (deterministic rule-based evaluation)
    - FraudAgent: < 0.65 (safety-critical, err on side of caution)
    - DecisionOrchestrationAgent: < 0.75 (high-stakes final decisions)

    DECISION LOGIC PRIORITY:
    1. Check for mandatory escalation rules FIRST (overrides everything)
    2. Check agent confidence scores (low confidence triggers escalation)
    3. Evaluate fraud risk level (high risk requires human review)
    4. Assess policy violations (rejection-level violations = final rejection)
    5. Consider fixable issues (rejected_with_instructions for clarifiable problems)
    6. Default to approval for compliant, low-risk expenses

    FRAUD RISK HANDLING:
    - High fraud risk: Always requires human review
    - Medium fraud risk: Escalate unless very clear policy compliance and high confidence
    - Low fraud risk: Can proceed with auto-approval if other factors align

    INFORMATION BOUNDARIES:
    - Internal reasoning: Can include fraud context and detailed analysis
    - External reasoning: Must exclude fraud details, provide sanitized explanations
    - Never reveal fraud detection methods or specific risk factors to users

    CRITICAL GUIDELINES:
    - Mandatory escalation rules always take precedence
    - Protect fraud detection information in external communications
    - Provide educational value in external reasoning when appropriate
    - Consider confidence scores across all agents in decision making
    - Balance automation efficiency with risk management
    """

    return Agent(
        name="DecisionOrchestrationAgent",
        instructions=instructions,
        output_type=AgentDecision,
    )


# TODO - implement this as a guardrail
def _validate_decision_compliance(
    parsed_result: dict,
    expense_report: ExpenseReport,
    categorization: ExpenseCategory,
    policy_evaluation: PolicyEvaluation,
    fraud_assessment: FraudAssessment,
) -> dict:
    """
    Validate that the decision complies with business rules and security requirements.

    Args:
        parsed_result: Parsed decision from agent
        expense_report: Original expense report
        categorization: Categorization results
        policy_evaluation: Policy evaluation results
        fraud_assessment: Fraud assessment results

    Returns:
        Validated and corrected decision
    """
    # Check mandatory escalation rules first
    is_mandatory_escalation = policy_evaluation.requires_human_review

    # Override decision if mandatory escalation is required
    if (
        is_mandatory_escalation
        and parsed_result.get("decision") != "requires_human_review"
    ):
        parsed_result["decision"] = "requires_human_review"
        parsed_result["is_mandatory_escalation"] = True
        parsed_result["escalation_reason"] = "mandatory_policy_requirement"

    # Validate decision against confidence thresholds
    low_confidence_agents = []
    if categorization.confidence < 0.70:
        low_confidence_agents.append("CategoryAgent")
    if policy_evaluation.confidence < 0.80:
        low_confidence_agents.append("PolicyEvaluationAgent")
    if fraud_assessment.confidence < 0.65:
        low_confidence_agents.append("FraudAgent")

    # Force escalation for low confidence
    if low_confidence_agents and parsed_result.get("decision") == "approved":
        parsed_result["decision"] = "requires_human_review"
        parsed_result["escalation_reason"] = "low_confidence_assessment"

    # Force escalation for high fraud risk
    if (
        fraud_assessment.overall_risk == "high"
        and parsed_result.get("decision") == "approved"
    ):
        parsed_result["decision"] = "requires_human_review"
        parsed_result["escalation_reason"] = "risk_assessment_required"

    # Sanitize external reasoning to remove fraud details
    external_reasoning = parsed_result.get("external_reasoning", "")

    # Remove fraud-related terms from external reasoning
    fraud_terms = ["fraud", "suspicious", "risk", "flag", "detection", "assessment"]
    external_reasoning_lower = external_reasoning.lower()

    if any(term in external_reasoning_lower for term in fraud_terms):
        # Replace with generic explanation based on decision type
        decision = parsed_result.get("decision", "requires_human_review")

        if decision == "requires_human_review":
            if is_mandatory_escalation:
                external_reasoning = (
                    "This expense requires mandatory human approval per company policy."
                )
            else:
                external_reasoning = "This expense requires additional review to ensure compliance with company policies."
        elif decision == "rejected_with_instructions":
            external_reasoning = "This expense requires additional information before it can be processed. Please review the submission guidelines."
        elif decision == "final_rejection":
            external_reasoning = "This expense does not meet company policy requirements and cannot be approved."
        else:
            external_reasoning = (
                "Expense has been processed according to company policies."
            )

    return {
        "decision": parsed_result.get("decision", "requires_human_review"),
        "internal_reasoning": parsed_result.get(
            "internal_reasoning", "Decision validation applied."
        ),
        "external_reasoning": external_reasoning,
        "escalation_reason": parsed_result.get("escalation_reason"),
        "is_mandatory_escalation": is_mandatory_escalation,
        "confidence": min(max(parsed_result.get("confidence", 0.5), 0.0), 1.0),
    }


def _fallback_agent_decision(
    expense_report: ExpenseReport,
    categorization: ExpenseCategory,
    policy_evaluation: PolicyEvaluation,
    fraud_assessment: FraudAssessment,
) -> AgentDecision:
    """
    Create a fallback decision when the agent fails.

    Args:
        expense_report: Original expense report
        categorization: Categorization results
        policy_evaluation: Policy evaluation results
        fraud_assessment: Fraud assessment results

    Returns:
        Conservative fallback AgentDecision
    """
    # Conservative fallback - escalate to human review for safety
    decision: str = "requires_human_review"

    # Check if there are serious policy violations that would require rejection
    if not policy_evaluation.compliant and len(policy_evaluation.violations) > 0:
        serious_violations = [
            v
            for v in policy_evaluation.violations
            if v.severity in ["critical", "high"]
        ]
        if serious_violations:
            decision = "final_rejection"

    # Check fraud risk
    if fraud_assessment.overall_risk == "high":
        decision = "requires_human_review"

    # Cast to proper literal type for mypy
    from typing import Literal, cast

    decision_literal = cast(
        Literal[
            "approved",
            "requires_human_review",
            "final_rejection",
            "rejected_with_instructions",
        ],
        decision,
    )

    return AgentDecision(
        decision=decision_literal,
        internal_reasoning="Fallback decision due to agent processing failure. Conservative approach applied.",
        external_reasoning="This expense requires additional review to ensure compliance with company policies due to processing complexity.",
        escalation_reason="system_processing_failure"
        if decision == "requires_human_review"
        else None,
        is_mandatory_escalation=policy_evaluation.requires_human_review,
        confidence=0.3,  # Low confidence for fallback decisions
    )
