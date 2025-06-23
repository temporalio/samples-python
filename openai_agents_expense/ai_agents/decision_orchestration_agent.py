"""
DecisionOrchestrationAgent - Make final approval decisions using all available context.

This agent is responsible for:
1. Making final approval decisions using all available context
2. Respecting mandatory escalation rules that override AI assessment
3. Combining policy evaluation and fraud assessment with confidence scores
4. Information Access: Private - sees all context but only outputs sanitized decisions
"""

from temporalio import workflow, activity

# Import models at module level for consistent type identity
from openai_agents_expense.models import (
    ExpenseReport, ExpenseCategory, PolicyEvaluation, 
    FraudAssessment, FinalDecision
)

# Import agent components and models
with workflow.unsafe.imports_passed_through():
    from agents import Agent, Runner


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
    4. "rejected_with_instructions" - Fixable issues where employee can provide clarification

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

    RESPONSE FORMAT:
    Always respond with a JSON object containing:
    {
        "decision": "approved|requires_human_review|final_rejection|rejected_with_instructions",
        "internal_reasoning": "detailed reasoning for administrators, includes fraud context",
        "external_reasoning": "sanitized reasoning for users, no fraud details exposed",
        "escalation_reason": "generic reason for human escalation or null",
        "is_mandatory_escalation": boolean,
        "confidence": float between 0 and 1
    }

    CRITICAL GUIDELINES:
    - Mandatory escalation rules always take precedence
    - Protect fraud detection information in external communications
    - Provide educational value in external reasoning when appropriate
    - Consider confidence scores across all agents in decision making
    - Balance automation efficiency with risk management
    """
    
    return Agent(
        name="DecisionOrchestrationAgent",
        instructions=instructions
    )


@activity.defn
async def make_final_decision(
    expense_report: ExpenseReport,
    categorization: ExpenseCategory,
    policy_evaluation: PolicyEvaluation,
    fraud_assessment: FraudAssessment
) -> FinalDecision:
    """
    Make the final expense approval decision by orchestrating all inputs.
    
    Args:
        expense_report: The expense report
        categorization: Results from CategoryAgent
        policy_evaluation: Results from PolicyEvaluationAgent
        fraud_assessment: Results from FraudAgent
        
    Returns:
        FinalDecision with approval decision and reasoning
    """
    
    activity.logger.info(f"Making final decision for expense {expense_report.expense_id}")
    
    # Create the decision orchestration agent
    agent = create_decision_orchestration_agent()
    
    # Prepare comprehensive input for the agent
    decision_input = f"""
    Please make the final approval decision for this expense by analyzing all available information:
    
    EXPENSE DETAILS:
    - Expense ID: {expense_report.expense_id}
    - Amount: ${expense_report.amount}
    - Description: {expense_report.description}
    - Vendor: {expense_report.vendor}
    - International Travel: {'Yes' if expense_report.is_international_travel else 'No'}
    
    CATEGORIZATION RESULTS:
    - Category: {categorization.category}
    - Confidence: {categorization.confidence}
    - Vendor Legitimate: {'Yes' if categorization.vendor_validation.is_legitimate else 'No'}
    - Categorization Reasoning: {categorization.reasoning}
    
    POLICY EVALUATION RESULTS:
    - Compliant: {'Yes' if policy_evaluation.compliant else 'No'}
    - Violations Count: {len(policy_evaluation.violations)}
    - Mandatory Human Review: {'Yes' if policy_evaluation.mandatory_human_review else 'No'}
    - Policy Confidence: {policy_evaluation.confidence}
    - Violations: {[f"{v.rule_name} ({v.severity})" for v in policy_evaluation.violations]}
    
    FRAUD ASSESSMENT RESULTS:
    - Overall Risk: {fraud_assessment.overall_risk}
    - Flags Count: {len(fraud_assessment.flags)}
    - Requires Human Review: {'Yes' if fraud_assessment.requires_human_review else 'No'}
    - Fraud Confidence: {fraud_assessment.confidence}
    - Flag Types: {[f.flag_type for f in fraud_assessment.flags]}
    
    CONFIDENCE ANALYSIS:
    - CategoryAgent: {categorization.confidence} (threshold: 0.70)
    - PolicyEvaluationAgent: {policy_evaluation.confidence} (threshold: 0.80)
    - FraudAgent: {fraud_assessment.confidence} (threshold: 0.65)
    
    CRITICAL REMINDERS:
    1. Check mandatory escalation rules FIRST - they override all other assessments
    2. Apply confidence thresholds for AI-driven escalation
    3. Protect fraud information in external reasoning
    4. Distinguish between fixable issues and serious concerns requiring investigation
    
    Make your final decision considering all factors and confidence levels.
    """
    
    try:
        # Run the agent to get the final decision
        result = await Runner.run(agent, input=decision_input)
        
        # Parse the agent's response
        import json
        
        try:
            # Extract JSON from the agent's response
            response_text = result.final_output
            
            # Find JSON in the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                parsed_result = json.loads(json_text)
                
                # Validate and sanitize the decision
                validated_result = _validate_decision_compliance(
                    parsed_result, expense_report, categorization, policy_evaluation, fraud_assessment
                )
                
                # Create final decision result
                final_decision = FinalDecision(
                    decision=validated_result["decision"],
                    internal_reasoning=validated_result["internal_reasoning"],
                    external_reasoning=validated_result["external_reasoning"],
                    escalation_reason=validated_result.get("escalation_reason"),
                    is_mandatory_escalation=validated_result["is_mandatory_escalation"],
                    confidence=validated_result["confidence"]
                )
                
                activity.logger.info(f"Final decision made: {final_decision.decision} (confidence: {final_decision.confidence})")
                return final_decision
                
            else:
                raise ValueError("No valid JSON found in agent response")
                
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            activity.logger.error(f"Failed to parse decision agent response: {e}")
            activity.logger.error(f"Agent response was: {result.final_output}")
            
            # Create fallback decision
            fallback_decision = _fallback_final_decision(
                expense_report, categorization, policy_evaluation, fraud_assessment
            )
            activity.logger.warning(f"Using fallback final decision: {fallback_decision.decision}")
            return fallback_decision
            
    except Exception as e:
        activity.logger.error(f"DecisionOrchestrationAgent failed for expense {expense_report.expense_id}: {e}")
        
        # Create fallback decision
        fallback_decision = _fallback_final_decision(
            expense_report, categorization, policy_evaluation, fraud_assessment
        )
        activity.logger.warning(f"Using fallback final decision due to agent failure: {fallback_decision.decision}")
        return fallback_decision


def _validate_decision_compliance(
    parsed_result: dict,
    expense_report: ExpenseReport,
    categorization: ExpenseCategory,
    policy_evaluation: PolicyEvaluation,
    fraud_assessment: FraudAssessment
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
    is_mandatory_escalation = policy_evaluation.mandatory_human_review
    
    # Override decision if mandatory escalation is required
    if is_mandatory_escalation and parsed_result.get("decision") != "requires_human_review":
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
    if fraud_assessment.overall_risk == "high" and parsed_result.get("decision") == "approved":
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
                external_reasoning = "This expense requires mandatory human approval per company policy."
            else:
                external_reasoning = "This expense requires additional review to ensure compliance with company policies."
        elif decision == "rejected_with_instructions":
            external_reasoning = "This expense requires additional information before it can be processed. Please review the submission guidelines."
        elif decision == "final_rejection":
            external_reasoning = "This expense does not meet company policy requirements and cannot be approved."
        else:
            external_reasoning = "Expense has been processed according to company policies."
    
    return {
        "decision": parsed_result.get("decision", "requires_human_review"),
        "internal_reasoning": parsed_result.get("internal_reasoning", "Decision validation applied."),
        "external_reasoning": external_reasoning,
        "escalation_reason": parsed_result.get("escalation_reason"),
        "is_mandatory_escalation": is_mandatory_escalation,
        "confidence": min(max(parsed_result.get("confidence", 0.5), 0.0), 1.0)
    }


def _fallback_final_decision(
    expense_report: ExpenseReport,
    categorization: ExpenseCategory,
    policy_evaluation: PolicyEvaluation,
    fraud_assessment: FraudAssessment
) -> FinalDecision:
    """
    Provide fallback decision when the agent fails.
    
    Args:
        expense_report: The expense report
        categorization: Categorization results
        policy_evaluation: Policy evaluation results
        fraud_assessment: Fraud assessment results
        
    Returns:
        Basic FinalDecision with rule-based logic
    """
    # Apply mandatory escalation rules first
    if policy_evaluation.mandatory_human_review:
        return FinalDecision(
            decision="requires_human_review",
            internal_reasoning="Mandatory escalation due to business rules (fallback decision).",
            external_reasoning="This expense requires mandatory human approval per company policy.",
            escalation_reason="mandatory_policy_requirement",
            is_mandatory_escalation=True,
            confidence=0.8
        )
    
    # Check confidence thresholds
    if (categorization.confidence < 0.70 or 
        policy_evaluation.confidence < 0.80 or 
        fraud_assessment.confidence < 0.65):
        return FinalDecision(
            decision="requires_human_review",
            internal_reasoning="Low confidence across agents requires human review (fallback decision).",
            external_reasoning="This expense requires additional review due to assessment uncertainty.",
            escalation_reason="low_confidence_assessment",
            is_mandatory_escalation=False,
            confidence=0.6
        )
    
    # Check for high fraud risk
    if fraud_assessment.overall_risk == "high":
        return FinalDecision(
            decision="requires_human_review",
            internal_reasoning="High fraud risk requires human review (fallback decision).",
            external_reasoning="This expense requires additional verification before processing.",
            escalation_reason="additional_verification_required",
            is_mandatory_escalation=False,
            confidence=0.7
        )
    
    # Check for policy violations
    rejection_violations = [v for v in policy_evaluation.violations if v.severity == "rejection"]
    if rejection_violations:
        return FinalDecision(
            decision="final_rejection",
            internal_reasoning="Policy violations with rejection severity (fallback decision).",
            external_reasoning="This expense violates company policy and cannot be approved.",
            escalation_reason=None,
            is_mandatory_escalation=False,
            confidence=0.8
        )
    
    # Default to approval for compliant expenses
    if policy_evaluation.compliant and fraud_assessment.overall_risk == "low":
        return FinalDecision(
            decision="approved",
            internal_reasoning="Policy compliant with low fraud risk (fallback decision).",
            external_reasoning="Expense approved for payment processing.",
            escalation_reason=None,
            is_mandatory_escalation=False,
            confidence=0.7
        )
    
    # Default to human review for uncertain cases
    return FinalDecision(
        decision="requires_human_review",
        internal_reasoning="Uncertain case requiring human judgment (fallback decision).",
        external_reasoning="This expense requires additional review before processing.",
        escalation_reason="manual_review_required",
        is_mandatory_escalation=False,
        confidence=0.5
    ) 