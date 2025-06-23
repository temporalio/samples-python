"""
PolicyEvaluationAgent - Evaluate expenses against departmental policies and business rules.

This agent is responsible for:
1. Applying transparent business rules and identifying policy violations
2. Evaluating categorized expenses against departmental policies
3. Determining mandatory escalation requirements
4. Information Access: Public - policy explanations are transparent to employees
"""

from datetime import timedelta, date
from temporalio import workflow, activity

# Import agent components and models
with workflow.unsafe.imports_passed_through():
    from agents import Agent, Runner
    from openai_agents_expense.models import (
        ExpenseReport, ExpenseCategory, PolicyEvaluation, 
        PolicyViolation
    )


def create_policy_evaluation_agent() -> Agent:
    """
    Create the PolicyEvaluationAgent for policy compliance checking.
    
    Returns:
        Configured Agent instance for policy evaluation
    """
    instructions = """
    You are a policy evaluation specialist responsible for ensuring expense compliance with departmental policies and business rules.

    DEPARTMENTAL POLICIES:

    1. FLIGHT LIMIT: No flights more than $500 without human approval
    2. INTERNATIONAL TRAVEL: All international travel requires human approval regardless of amount
    3. PERSONAL SHOPPING: No personal shopping expenses allowed (automatic rejection)
    4. RECEIPT REQUIREMENTS: All expenses over $75 require receipt documentation
    5. LATE SUBMISSION: Expenses older than 60 days require manager approval
    6. EQUIPMENT THRESHOLD: Any equipment/hardware over $250 requires human approval
    7. CLIENT ENTERTAINMENT: Entertainment expenses require client name and business justification

    POLICY EVALUATION PROCESS:
    1. Review the expense details and categorization results
    2. Apply all relevant policies based on category, amount, and context
    3. Identify any policy violations with specific details
    4. Determine if mandatory human review is required (separate from AI-driven review)
    5. Calculate confidence based on rule clarity and application certainty
    6. Provide transparent policy explanations for educational value

    MANDATORY HUMAN REVIEW TRIGGERS (override all other assessments):
    - International travel (regardless of AI assessment)
    - Flight expenses over $500 (regardless of AI assessment)
    - Equipment/hardware over $250 (regardless of AI assessment)
    - Late submissions over 60 days (regardless of AI assessment)

    POLICY VIOLATION TYPES:
    - "policy_violation": Direct violation of established policy
    - "documentation_missing": Required documentation not provided
    - "threshold_exceeded": Amount exceeds policy threshold
    - "information_missing": Required information not provided

    SEVERITY LEVELS:
    - "warning": Minor issue that should be noted
    - "requires_review": Issue that needs human evaluation
    - "rejection": Clear violation requiring rejection

    RESPONSE FORMAT:
    Always respond with a JSON object containing:
    {
        "compliant": boolean,
        "violations": [
            {
                "rule_name": "specific policy rule name",
                "violation_type": "policy_violation|documentation_missing|threshold_exceeded|information_missing",
                "severity": "warning|requires_review|rejection",
                "details": "specific explanation of the violation",
                "threshold_amount": null or decimal amount if applicable
            }
        ],
        "reasoning": "detailed explanation of policy evaluation",
        "requires_human_review": boolean (based on policy complexity, not fraud),
        "mandatory_human_review": boolean (based on mandatory escalation rules),
        "policy_explanation": "clear explanation of applicable policies for employee education",
        "confidence": float between 0 and 1
    }

    IMPORTANT GUIDELINES:
    - Be transparent about all policy requirements (this is a public agent)
    - Provide educational explanations to help employees understand policies
    - Distinguish between mandatory escalation and AI-driven review needs
    - Focus on rule-based evaluation, not subjective judgment
    - Include specific threshold amounts and requirements in explanations
    """
    
    return Agent(
        name="PolicyEvaluationAgent",
        instructions=instructions
    )


@activity.defn
async def evaluate_policy_compliance(
    expense_report: ExpenseReport, 
    categorization: ExpenseCategory
) -> PolicyEvaluation:
    """
    Evaluate an expense report for policy compliance.
    
    Args:
        expense_report: The expense report to evaluate
        categorization: Results from CategoryAgent
        
    Returns:
        PolicyEvaluation with compliance results
    """
    
    activity.logger.info(f"Evaluating policy compliance for expense {expense_report.expense_id}")
    
    # Create the policy evaluation agent
    agent = create_policy_evaluation_agent()
    
    # Calculate days since expense occurred
    days_since_expense = (expense_report.submission_date - expense_report.date).days
    
    # Prepare input for the agent
    policy_input = f"""
    Please evaluate this expense for policy compliance:
    
    Expense Details:
    - Expense ID: {expense_report.expense_id}
    - Amount: ${expense_report.amount}
    - Description: {expense_report.description}
    - Vendor: {expense_report.vendor}
    - Date: {expense_report.date}
    - Submission Date: {expense_report.submission_date}
    - Days since expense occurred: {days_since_expense}
    - Department: {expense_report.department}
    - Receipt provided: {'Yes' if expense_report.receipt_provided else 'No'}
    - Client Name: {expense_report.client_name or 'Not provided'}
    - Business Justification: {expense_report.business_justification or 'Not provided'}
    - International Travel: {'Yes' if expense_report.is_international_travel else 'No'}
    
    Categorization Results:
    - Category: {categorization.category}
    - Vendor Legitimacy: {'Legitimate' if categorization.vendor_validation.is_legitimate else 'Not verified/Suspicious'}
    - Categorization Confidence: {categorization.confidence}
    
    Please evaluate this expense against all applicable departmental policies and identify any violations. Pay special attention to mandatory human review requirements that override AI assessment.
    """
    
    try:
        # Run the agent to get policy evaluation results
        result = await Runner.run(agent, input=policy_input)
        
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
                
                # Create policy violation objects
                violations = []
                for violation_data in parsed_result.get("violations", []):
                    violation = PolicyViolation(
                        rule_name=violation_data["rule_name"],
                        violation_type=violation_data["violation_type"],
                        severity=violation_data["severity"],
                        details=violation_data["details"],
                        threshold_amount=violation_data.get("threshold_amount")
                    )
                    violations.append(violation)
                
                # Create policy evaluation result
                policy_result = PolicyEvaluation(
                    compliant=parsed_result["compliant"],
                    violations=violations,
                    reasoning=parsed_result["reasoning"],
                    requires_human_review=parsed_result["requires_human_review"],
                    mandatory_human_review=parsed_result["mandatory_human_review"],
                    policy_explanation=parsed_result["policy_explanation"],
                    confidence=parsed_result["confidence"]
                )
                
                activity.logger.info(f"Policy evaluation completed: {'Compliant' if policy_result.compliant else 'Non-compliant'} (confidence: {policy_result.confidence})")
                return policy_result
                
            else:
                raise ValueError("No valid JSON found in agent response")
                
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            activity.logger.error(f"Failed to parse agent response: {e}")
            activity.logger.error(f"Agent response was: {result.final_output}")
            
            # Create fallback result
            fallback_policy = _fallback_policy_evaluation(expense_report, categorization)
            activity.logger.warning(f"Using fallback policy evaluation")
            return fallback_policy
            
    except Exception as e:
        activity.logger.error(f"PolicyEvaluationAgent failed for expense {expense_report.expense_id}: {e}")
        
        # Create fallback result
        fallback_policy = _fallback_policy_evaluation(expense_report, categorization)
        activity.logger.warning(f"Using fallback policy evaluation due to agent failure")
        return fallback_policy


def _fallback_policy_evaluation(
    expense_report: ExpenseReport, 
    categorization: ExpenseCategory
) -> PolicyEvaluation:
    """
    Provide fallback policy evaluation when the agent fails.
    
    Args:
        expense_report: The expense report to evaluate
        categorization: Categorization results
        
    Returns:
        Basic PolicyEvaluation with rule-based assessment
    """
    violations = []
    
    # Apply basic policy rules
    
    # Check receipt requirement (over $75)
    if expense_report.amount > 75 and not expense_report.receipt_provided:
        violations.append(PolicyViolation(
            rule_name="Receipt Documentation",
            violation_type="documentation_missing",
            severity="requires_review",
            details=f"Expenses over $75 require receipt documentation. Amount is ${expense_report.amount} without receipt provided.",
            threshold_amount=75.00
        ))
    
    # Check international travel (mandatory escalation)
    mandatory_human_review = expense_report.is_international_travel
    
    # Check flight limit ($500)
    if categorization.category == "Travel & Transportation" and "flight" in expense_report.description.lower():
        if expense_report.amount > 500:
            mandatory_human_review = True
    
    # Check equipment threshold ($250)
    if categorization.category == "Equipment & Hardware" and expense_report.amount > 250:
        mandatory_human_review = True
    
    # Check late submission (60 days)
    days_since_expense = (expense_report.submission_date - expense_report.date).days
    if days_since_expense > 60:
        mandatory_human_review = True
    
    # Check entertainment requirements
    if categorization.category == "Meals & Entertainment":
        if not expense_report.client_name and not expense_report.business_justification:
            violations.append(PolicyViolation(
                rule_name="Client Entertainment Documentation",
                violation_type="information_missing",
                severity="requires_review",
                details="Entertainment expenses require client name and business justification.",
                threshold_amount=None
            ))
    
    # Check for personal shopping
    if "personal" in expense_report.description.lower():
        violations.append(PolicyViolation(
            rule_name="Personal Shopping Prohibition",
            violation_type="policy_violation",
            severity="rejection",
            details="Personal shopping expenses are not allowed under departmental policy.",
            threshold_amount=None
        ))
    
    compliant = len([v for v in violations if v.severity == "rejection"]) == 0
    
    return PolicyEvaluation(
        compliant=compliant,
        violations=violations,
        reasoning=f"Fallback policy evaluation applied basic rules. Found {len(violations)} policy issues.",
        requires_human_review=len(violations) > 0,
        mandatory_human_review=mandatory_human_review,
        policy_explanation="Basic policy rules applied: receipt requirements, mandatory escalations, and documentation requirements.",
        confidence=0.6  # Lower confidence for fallback
    ) 