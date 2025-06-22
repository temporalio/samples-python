"""
ResponseAgent - Generate personalized responses to expense submitters.

This agent is responsible for:
1. Generating human-friendly explanations of approval/rejection decisions
2. Providing appropriate instructions based on decision type
3. Maintaining professional, educational tone
4. Information Access: Public - only sees final decisions, policy explanations, and categorization details
"""

from temporalio import workflow

# Import agent components and models
with workflow.unsafe.imports_passed_through():
    from agents import Agent, Runner
    from openai_agents_expense.models import (
        ExpenseReport, ExpenseCategory, PolicyEvaluation, 
        FinalDecision, ExpenseResponse
    )


def create_response_agent() -> Agent:
    """
    Create the ResponseAgent for generating user responses.
    
    Returns:
        Configured Agent instance for response generation
    """
    instructions = """
    You are a professional communication specialist responsible for generating clear, helpful responses to expense submitters.

    RESPONSE PRINCIPLES:
    1. Maintain professional, supportive tone in all communications
    2. Provide educational value to help employees understand policies
    3. Give clear, actionable instructions when needed
    4. Be transparent about categorization and policy reasoning
    5. Never include fraud detection details or sensitive information

    DECISION TYPES AND RESPONSE APPROACH:

    1. APPROVED:
    - Positive, confirmatory tone
    - Brief explanation of categorization and policy compliance
    - Clear statement about payment processing
    - Acknowledge proper documentation when applicable

    2. FINAL REJECTION:
    - Professional but firm explanation
    - Clear policy violation details
    - Educational context about policy requirements
    - No resubmission path offered (final decision)

    3. REJECTED WITH INSTRUCTIONS:
    - Supportive tone focused on resolution
    - Specific instructions for fixing the issue
    - Clear resubmission guidance
    - Educational elements about proper submission

    4. REQUIRES HUMAN REVIEW:
    - Professional explanation of review process
    - Generic reasons for escalation (no fraud details)
    - Timeline expectations when appropriate
    - Reassurance about legitimate expenses

    CONTENT GUIDELINES:
    - Include policy explanations for educational value
    - Summarize categorization findings transparently
    - Provide specific next steps when applicable
    - Use clear, jargon-free language
    - Maintain consistent professional tone

    SECURITY REQUIREMENTS:
    - Never mention fraud detection, risk assessment, or security concerns
    - Exclude all fraud-related terminology from responses
    - Focus on policy compliance and documentation requirements
    - Keep escalation reasons generic and professional

    RESPONSE FORMAT:
    Always respond with a JSON object containing:
    {
        "message": "main response message with appropriate tone and instructions",
        "decision_summary": "brief summary of the decision with any required actions",
        "policy_explanation": "relevant policy explanations for educational value or null",
        "categorization_summary": "summary of expense categorization and vendor validation findings"
    }

    TONE GUIDELINES:
    - Approved: Positive and confirming
    - Rejected with instructions: Helpful and solution-oriented
    - Final rejection: Professional and educational
    - Human review: Reassuring and informative
    """
    
    return Agent(
        name="ResponseAgent",
        instructions=instructions
    )


async def generate_expense_response(
    expense_report: ExpenseReport,
    categorization: ExpenseCategory,
    policy_evaluation: PolicyEvaluation,
    final_decision: FinalDecision
) -> ExpenseResponse:
    """
    Generate a personalized response for the expense submitter.
    
    Args:
        expense_report: The expense report
        categorization: Results from CategoryAgent
        policy_evaluation: Results from PolicyEvaluationAgent
        final_decision: Results from DecisionOrchestrationAgent
        
    Returns:
        ExpenseResponse with user-friendly message and explanations
    """
    logger = workflow.logger
    logger.info(f"Generating response for expense {expense_report.expense_id}")
    
    # Create the response agent
    agent = create_response_agent()
    
    # Prepare input for the agent (excluding fraud details)
    response_input = f"""
    Please generate a professional, helpful response for this expense submission:
    
    EXPENSE DETAILS:
    - Expense ID: {expense_report.expense_id}
    - Amount: ${expense_report.amount}
    - Description: {expense_report.description}
    - Vendor: {expense_report.vendor}
    - Department: {expense_report.department}
    
    DECISION MADE:
    - Decision: {final_decision.decision}
    - External Reasoning: {final_decision.external_reasoning}
    - Mandatory Escalation: {'Yes' if final_decision.is_mandatory_escalation else 'No'}
    
    CATEGORIZATION RESULTS:
    - Category: {categorization.category}
    - Vendor Legitimacy: {'Verified' if categorization.vendor_validation.is_legitimate else 'Could not verify'}
    - Vendor Search Summary: {categorization.vendor_validation.web_search_summary}
    
    POLICY EVALUATION:
    - Policy Compliant: {'Yes' if policy_evaluation.compliant else 'No'}
    - Policy Explanation: {policy_evaluation.policy_explanation}
    - Violations: {[f"{v.rule_name}: {v.details}" for v in policy_evaluation.violations] if policy_evaluation.violations else "None"}
    
    RESPONSE REQUIREMENTS:
    - Use appropriate tone for the decision type
    - Include educational policy information when relevant
    - Provide clear next steps if action is needed
    - Maintain professional, supportive communication
    - Do NOT mention fraud, risk, or security concerns
    
    Generate a complete response that helps the employee understand the decision and any required actions.
    """
    
    try:
        # Run the agent to get the response
        result = await Runner.run(agent, input=response_input)
        
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
                
                # Validate and sanitize the response
                validated_result = _validate_response_content(parsed_result, final_decision)
                
                # Create expense response result
                expense_response = ExpenseResponse(
                    message=validated_result["message"],
                    decision_summary=validated_result["decision_summary"],
                    policy_explanation=validated_result.get("policy_explanation"),
                    categorization_summary=validated_result["categorization_summary"]
                )
                
                logger.info(f"Response generated for expense {expense_report.expense_id}")
                return expense_response
                
            else:
                raise ValueError("No valid JSON found in agent response")
                
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"Failed to parse response agent output: {e}")
            logger.error(f"Agent response was: {result.final_output}")
            
            # Create fallback response
            fallback_response = _fallback_expense_response(
                expense_report, categorization, policy_evaluation, final_decision
            )
            logger.warning(f"Using fallback response")
            return fallback_response
            
    except Exception as e:
        logger.error(f"ResponseAgent failed for expense {expense_report.expense_id}: {e}")
        
        # Create fallback response
        fallback_response = _fallback_expense_response(
            expense_report, categorization, policy_evaluation, final_decision
        )
        logger.warning(f"Using fallback response due to agent failure")
        return fallback_response


def _validate_response_content(parsed_result: dict, final_decision: FinalDecision) -> dict:
    """
    Validate that the response content is appropriate and secure.
    
    Args:
        parsed_result: Parsed response from agent
        final_decision: The final decision made
        
    Returns:
        Validated and sanitized response
    """
    # Forbidden terms that should not appear in user responses
    forbidden_terms = [
        "fraud", "suspicious", "risk", "flag", "detection", "assessment", 
        "security", "threat", "investigation", "algorithm", "pattern"
    ]
    
    # Sanitize message
    message = parsed_result.get("message", "")
    message_lower = message.lower()
    
    if any(term in message_lower for term in forbidden_terms):
        # Replace with generic message based on decision type
        decision = final_decision.decision
        
        if decision == "approved":
            message = "Your expense has been approved and will be processed for payment."
        elif decision == "final_rejection":
            message = "Your expense cannot be approved due to policy requirements. Please review our expense policy for guidance on reimbursable expenses."
        elif decision == "rejected_with_instructions":
            message = "Your expense requires additional information before it can be processed. Please review the submission requirements and resubmit with the necessary details."
        else:  # requires_human_review
            message = "Your expense has been submitted for review. Our team will examine the submission and contact you if additional information is needed."
    
    # Sanitize decision summary
    decision_summary = parsed_result.get("decision_summary", "")
    summary_lower = decision_summary.lower()
    
    if any(term in summary_lower for term in forbidden_terms):
        decision = final_decision.decision
        
        if decision == "approved":
            decision_summary = "Approved - Expense approved for payment processing"
        elif decision == "final_rejection":
            decision_summary = "Rejected - Does not meet policy requirements"
        elif decision == "rejected_with_instructions":
            decision_summary = "Additional Information Needed - Please resubmit with required details"
        else:  # requires_human_review
            decision_summary = "Under Review - Additional review required"
    
    # Sanitize policy explanation
    policy_explanation = parsed_result.get("policy_explanation", "")
    if policy_explanation:
        policy_lower = policy_explanation.lower()
        if any(term in policy_lower for term in forbidden_terms):
            policy_explanation = "Please refer to the employee handbook for detailed expense policy information."
    
    # Sanitize categorization summary
    categorization_summary = parsed_result.get("categorization_summary", "")
    cat_summary_lower = categorization_summary.lower()
    
    if any(term in cat_summary_lower for term in forbidden_terms):
        categorization_summary = "Expense categorization completed based on description and vendor information."
    
    return {
        "message": message,
        "decision_summary": decision_summary,
        "policy_explanation": policy_explanation if policy_explanation else None,
        "categorization_summary": categorization_summary
    }


def _fallback_expense_response(
    expense_report: ExpenseReport,
    categorization: ExpenseCategory,
    policy_evaluation: PolicyEvaluation,
    final_decision: FinalDecision
) -> ExpenseResponse:
    """
    Provide fallback response when the agent fails.
    
    Args:
        expense_report: The expense report
        categorization: Categorization results
        policy_evaluation: Policy evaluation results
        final_decision: Final decision results
        
    Returns:
        Basic ExpenseResponse with appropriate messaging
    """
    decision = final_decision.decision
    
    # Generate appropriate message based on decision type
    if decision == "approved":
        message = f"Your expense for ${expense_report.amount} has been approved and will be processed for payment. The expense was correctly categorized and meets all policy requirements."
        decision_summary = "Approved - Expense approved for payment processing"
        
    elif decision == "final_rejection":
        message = f"Your expense for ${expense_report.amount} cannot be approved as it does not meet company policy requirements. Please review our expense policy for guidance on reimbursable expenses."
        decision_summary = "Rejected - Does not meet policy requirements"
        
    elif decision == "rejected_with_instructions":
        message = f"Your expense for ${expense_report.amount} requires additional information before it can be processed. Please review the submission requirements and resubmit with the necessary details."
        decision_summary = "Additional Information Needed - Please resubmit with required details"
        
    else:  # requires_human_review
        if final_decision.is_mandatory_escalation:
            message = f"Your expense for ${expense_report.amount} has been submitted for mandatory review as required by company policy. Your submission will be reviewed promptly."
            decision_summary = "Mandatory Review Required - Per company policy"
        else:
            message = f"Your expense for ${expense_report.amount} has been submitted for additional review. Our team will examine the submission and contact you if additional information is needed."
            decision_summary = "Under Review - Additional review required"
    
    # Policy explanation
    policy_explanation = None
    if policy_evaluation.violations:
        policy_explanation = "Please ensure all future expense submissions include proper documentation and meet policy requirements."
    elif decision == "approved":
        policy_explanation = "This expense meets all policy requirements for reimbursement."
    
    # Categorization summary
    vendor_status = "verified" if categorization.vendor_validation.is_legitimate else "could not be verified"
    categorization_summary = f"Categorized as {categorization.category}. Vendor {expense_report.vendor} {vendor_status} through validation process."
    
    return ExpenseResponse(
        message=message,
        decision_summary=decision_summary,
        policy_explanation=policy_explanation,
        categorization_summary=categorization_summary
    ) 