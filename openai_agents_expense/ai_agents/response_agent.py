"""
ResponseAgent - Generate personalized responses to expense submitters.

This agent is responsible for:
1. Generating human-friendly explanations of approval/rejection decisions
2. Providing appropriate instructions based on decision type
3. Maintaining professional, educational tone
4. Information Access: Public - only sees final decisions, policy explanations, and categorization details
"""

from temporalio import workflow, activity

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


@activity.defn
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
    
    
    # Agent start logging
    activity.logger.info(
        f"📝 RESPONSE_AGENT_START: Starting response generation",
        extra={
            "expense_id": expense_report.expense_id,
            "agent": "ResponseAgent",
            "decision": final_decision.decision,
            "category": categorization.category,
            "policy_compliant": policy_evaluation.compliant,
            "stage": "start"
        }
    )
    
    # Create the response agent
    activity.logger.info(
        f"🤖 AGENT_CREATION: Creating ResponseAgent instance",
        extra={
            "expense_id": expense_report.expense_id,
            "agent": "ResponseAgent",
            "stage": "agent_creation"
        }
    )
    
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
    
    activity.logger.info(
        f"🎯 AGENT_INPUT: Prepared response agent input",
        extra={
            "expense_id": expense_report.expense_id,
            "agent": "ResponseAgent",
            "decision_type": final_decision.decision,
            "input_length": len(response_input),
            "violations_count": len(policy_evaluation.violations),
            "stage": "input_preparation"
        }
    )
    
    try:
        # Run the agent to get the response
        activity.logger.info(
            f"🚀 AGENT_EXECUTION: Running ResponseAgent",
            extra={
                "expense_id": expense_report.expense_id,
                "agent": "ResponseAgent",
                "stage": "execution"
            }
        )
        
        result = await Runner.run(agent, input=response_input)
        
        activity.logger.info(
            f"✅ AGENT_RESPONSE: ResponseAgent execution completed",
            extra={
                "expense_id": expense_report.expense_id,
                "agent": "ResponseAgent",
                "response_length": len(result.final_output) if hasattr(result, 'final_output') else 0,
                "stage": "response_received"
            }
        )
        
        # Parse the agent's response
        import json
        
        try:
            # Extract JSON from the agent's response
            response_text = result.final_output
            
            activity.logger.info(
                f"🔍 RESPONSE_PARSING: Parsing agent response",
                extra={
                    "expense_id": expense_report.expense_id,
                    "agent": "ResponseAgent",
                    "response_text_length": len(response_text),
                    "stage": "response_parsing"
                }
            )
            
            # Find JSON in the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                parsed_result = json.loads(json_text)
                
                activity.logger.info(
                    f"📊 JSON_PARSED: Successfully parsed response",
                    extra={
                        "expense_id": expense_report.expense_id,
                        "agent": "ResponseAgent",
                        "has_message": "message" in parsed_result,
                        "has_decision_summary": "decision_summary" in parsed_result,
                        "has_policy_explanation": "policy_explanation" in parsed_result,
                        "has_categorization_summary": "categorization_summary" in parsed_result,
                        "stage": "json_parsing_success"
                    }
                )
                
                # Validate and sanitize the response
                validated_result = _validate_response_content(parsed_result, final_decision)
                
                activity.logger.info(
                    f"✅ RESPONSE_VALIDATED: Response content validated",
                    extra={
                        "expense_id": expense_report.expense_id,
                        "agent": "ResponseAgent",
                        "validation_applied": True,
                        "message_length": len(validated_result["message"]),
                        "stage": "validation_complete"
                    }
                )
                
                # Create expense response result
                expense_response = ExpenseResponse(
                    message=validated_result["message"],
                    decision_summary=validated_result["decision_summary"],
                    policy_explanation=validated_result.get("policy_explanation"),
                    categorization_summary=validated_result["categorization_summary"]
                )
                
                activity.logger.info(
                    f"✅ RESPONSE_AGENT_SUCCESS: Response generation completed successfully",
                    extra={
                        "expense_id": expense_report.expense_id,
                        "agent": "ResponseAgent",
                        "message_length": len(expense_response.message),
                        "has_policy_explanation": expense_response.policy_explanation is not None,
                        "stage": "success"
                    }
                )
                
                return expense_response
                
            else:
                raise ValueError("No valid JSON found in agent response")
                
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            activity.logger.error(
                f"🚨 PARSING_ERROR: Failed to parse ResponseAgent output",
                extra={
                    "expense_id": expense_report.expense_id,
                    "agent": "ResponseAgent",
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "response_preview": result.final_output[:200] if hasattr(result, 'final_output') else "No output",
                    "stage": "parsing_error"
                }
            )
            
            # Create fallback response
            fallback_response = _fallback_expense_response(
                expense_report, categorization, policy_evaluation, final_decision
            )
            
            activity.logger.warning(
                f"⚠️ RESPONSE_FALLBACK: Using fallback response due to parsing error",
                extra={
                    "expense_id": expense_report.expense_id,
                    "agent": "ResponseAgent",
                    "fallback_decision": final_decision.decision,
                    "stage": "fallback_parsing"
                }
            )
            
            return fallback_response
            
    except Exception as e:
        activity.logger.error(
            f"🚨 RESPONSE_AGENT_ERROR: ResponseAgent execution failed",
            extra={
                "expense_id": expense_report.expense_id,
                "agent": "ResponseAgent",
                "error": str(e),
                "error_type": type(e).__name__,
                "stage": "execution_error"
            }
        )
        
        # Create fallback response
        fallback_response = _fallback_expense_response(
            expense_report, categorization, policy_evaluation, final_decision
        )
        
        activity.logger.warning(
            f"⚠️ RESPONSE_FALLBACK: Using fallback response due to agent failure",
            extra={
                "expense_id": expense_report.expense_id,
                "agent": "ResponseAgent",
                "fallback_decision": final_decision.decision,
                "stage": "fallback_execution"
            }
        )
        
        return fallback_response


def _validate_response_content(parsed_result: dict, final_decision: FinalDecision) -> dict:
    """
    Validate and sanitize response content for security and consistency.
    
    Args:
        parsed_result: Parsed response from agent
        final_decision: Final decision for context
        
    Returns:
        Validated response content
    """
    
    
    activity.logger.info(
        f"🔍 VALIDATION_START: Starting response content validation",
        extra={
            "agent": "ResponseAgent",
            "decision": final_decision.decision,
            "validation_stage": "start"
        }
    )
    
    # Ensure required fields exist
    validated = {
        "message": parsed_result.get("message", "Your expense has been processed."),
        "decision_summary": parsed_result.get("decision_summary", f"Decision: {final_decision.decision}"),
        "policy_explanation": parsed_result.get("policy_explanation"),
        "categorization_summary": parsed_result.get("categorization_summary", "Expense categorized for processing.")
    }
    
    # Sanitize content - remove any fraud-related terms that shouldn't be in public responses
    fraud_terms = ["fraud", "suspicious", "risk assessment", "detection", "flag", "security concern"]
    
    for field_name, content in validated.items():
        if content and isinstance(content, str):
            original_content = content
            for term in fraud_terms:
                if term.lower() in content.lower():
                    # Replace with generic language
                    content = content.replace(term, "review")
                    activity.logger.warning(
                        f"⚠️ CONTENT_SANITIZED: Removed sensitive term from response",
                        extra={
                            "agent": "ResponseAgent",
                            "field": field_name,
                            "removed_term": term,
                            "validation_stage": "sanitization"
                        }
                    )
            validated[field_name] = content
    
    activity.logger.info(
        f"✅ VALIDATION_COMPLETE: Response content validation completed",
        extra={
            "agent": "ResponseAgent",
            "validated_fields": list(validated.keys()),
            "validation_stage": "complete"
        }
    )
    
    return validated


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
    
    
    activity.logger.info(
        f"🔧 FALLBACK_START: Starting fallback response generation",
        extra={
            "expense_id": expense_report.expense_id,
            "agent": "ResponseAgent",
            "decision": final_decision.decision,
            "fallback_method": "template_based",
            "stage": "fallback_start"
        }
    )
    
    decision = final_decision.decision
    
    # Generate appropriate message based on decision type
    if decision == "approved":
        message = f"Your expense for ${expense_report.amount} has been approved and will be processed for payment. The expense was correctly categorized and meets all policy requirements."
        decision_summary = "Approved - Expense approved for payment processing"
        
        activity.logger.info(
            f"📝 APPROVAL_MESSAGE: Generated approval message",
            extra={
                "expense_id": expense_report.expense_id,
                "agent": "ResponseAgent",
                "amount": str(expense_report.amount),
                "stage": "approval_message"
            }
        )
        
    elif decision == "final_rejection":
        message = f"Your expense for ${expense_report.amount} cannot be approved as it does not meet company policy requirements. Please review our expense policy for guidance on reimbursable expenses."
        decision_summary = "Rejected - Does not meet policy requirements"
        
        activity.logger.info(
            f"❌ REJECTION_MESSAGE: Generated rejection message",
            extra={
                "expense_id": expense_report.expense_id,
                "agent": "ResponseAgent",
                "amount": str(expense_report.amount),
                "stage": "rejection_message"
            }
        )
        
    elif decision == "rejected_with_instructions":
        message = f"Your expense for ${expense_report.amount} requires additional information before it can be processed. Please review the submission requirements and resubmit with the necessary details."
        decision_summary = "Additional Information Needed - Please resubmit with required details"
        
        activity.logger.info(
            f"📋 INSTRUCTIONS_MESSAGE: Generated instructions message",
            extra={
                "expense_id": expense_report.expense_id,
                "agent": "ResponseAgent",
                "amount": str(expense_report.amount),
                "stage": "instructions_message"
            }
        )
        
    else:  # requires_human_review
        if final_decision.is_mandatory_escalation:
            message = f"Your expense for ${expense_report.amount} has been submitted for mandatory review as required by company policy. Your submission will be reviewed promptly."
            decision_summary = "Mandatory Review Required - Per company policy"
        else:
            message = f"Your expense for ${expense_report.amount} has been submitted for additional review. Our team will examine the submission and contact you if additional information is needed."
            decision_summary = "Under Review - Additional review required"
        
        activity.logger.info(
            f"👥 REVIEW_MESSAGE: Generated review message",
            extra={
                "expense_id": expense_report.expense_id,
                "agent": "ResponseAgent",
                "amount": str(expense_report.amount),
                "is_mandatory": final_decision.is_mandatory_escalation,
                "stage": "review_message"
            }
        )
    
    # Policy explanation
    policy_explanation = None
    if policy_evaluation.violations:
        policy_explanation = "Please ensure all future expense submissions include proper documentation and meet policy requirements."
    elif decision == "approved":
        policy_explanation = "This expense meets all policy requirements for reimbursement."
    
    # Categorization summary
    vendor_status = "verified" if categorization.vendor_validation.is_legitimate else "could not be verified"
    categorization_summary = f"Categorized as {categorization.category}. Vendor {expense_report.vendor} {vendor_status} through validation process."
    
    fallback_response = ExpenseResponse(
        message=message,
        decision_summary=decision_summary,
        policy_explanation=policy_explanation,
        categorization_summary=categorization_summary
    )
    
    activity.logger.info(
        f"✅ FALLBACK_COMPLETE: Fallback response generation completed",
        extra={
            "expense_id": expense_report.expense_id,
            "agent": "ResponseAgent",
            "decision": decision,
            "message_length": len(fallback_response.message),
            "has_policy_explanation": fallback_response.policy_explanation is not None,
            "stage": "fallback_complete"
        }
    )
    
    return fallback_response 