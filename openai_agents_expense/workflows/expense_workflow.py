"""
Main ExpenseWorkflow - Orchestrates AI agents for expense processing with enhanced decision-making.

This workflow coordinates:
1. CategoryAgent (categorization and vendor validation)
2. PolicyEvaluationAgent and FraudAgent (parallel processing)
3. DecisionOrchestrationAgent (final decision making)
4. ResponseAgent (user communication)
5. Human-in-the-loop integration for escalated cases
"""

from datetime import datetime, timedelta
from temporalio import workflow
from temporalio.exceptions import ApplicationError

# Import models and agent functions
with workflow.unsafe.imports_passed_through():
    from openai_agents_expense.models import (
        ExpenseReport, ExpenseProcessingResult, ExpenseStatus
    )
    from openai_agents_expense.ai_agents.category_agent import categorize_expense
    from openai_agents_expense.ai_agents.policy_evaluation_agent import evaluate_policy_compliance
    from openai_agents_expense.ai_agents.fraud_agent import assess_fraud_risk
    from openai_agents_expense.ai_agents.decision_orchestration_agent import make_final_decision
    from openai_agents_expense.ai_agents.response_agent import generate_expense_response


@workflow.defn
class ExpenseWorkflow:
    """
    Main expense processing workflow with OpenAI Agents integration.
    """
    
    def __init__(self):
        self._status = ExpenseStatus(
            expense_id="",
            current_status="submitted",
            processing_history=["Expense submitted for processing"],
            last_updated=workflow.now(),
            estimated_completion=None
        )
        self._processing_result: ExpenseProcessingResult = None
    
    @workflow.run
    async def run(self, expense_report: ExpenseReport) -> str:
        """
        Process an expense report using AI agents.
        
        Args:
            expense_report: The expense report to process
            
        Returns:
            Final status of the expense processing
        """
        logger = workflow.logger
        
        # Workflow initialization logging
        logger.info(
            f"🚀 WORKFLOW_START: Processing expense {expense_report.expense_id}",
            extra={
                "expense_id": expense_report.expense_id,
                "amount": str(expense_report.amount),
                "vendor": expense_report.vendor,
                "description": expense_report.description,
                "department": expense_report.department,
                "employee_id": expense_report.employee_id,
                "is_international_travel": expense_report.is_international_travel,
                "receipt_provided": expense_report.receipt_provided,
                "workflow_stage": "initialization"
            }
        )
        
        # Initialize status tracking
        self._status.expense_id = expense_report.expense_id
        self._update_status("processing", "AI agents processing expense report")
        
        try:
            # Step 1: CategoryAgent - Categorize expense and validate vendor
            logger.info(
                f"📋 AGENT_START: CategoryAgent processing expense {expense_report.expense_id}",
                extra={
                    "expense_id": expense_report.expense_id,
                    "agent": "CategoryAgent",
                    "workflow_stage": "categorization",
                    "step": 1
                }
            )
            
            categorization_start_time = workflow.now()
            categorization = await categorize_expense(expense_report)
            categorization_duration = (workflow.now() - categorization_start_time).total_seconds()
            
            logger.info(
                f"✅ AGENT_COMPLETE: CategoryAgent finished for expense {expense_report.expense_id}",
                extra={
                    "expense_id": expense_report.expense_id,
                    "agent": "CategoryAgent",
                    "category": categorization.category,
                    "confidence": categorization.confidence,
                    "vendor_legitimate": categorization.vendor_validation.is_legitimate,
                    "vendor_confidence": categorization.vendor_validation.confidence_score,
                    "duration_seconds": categorization_duration,
                    "workflow_stage": "categorization_complete",
                    "step": 1
                }
            )
            
            # Check if categorization confidence triggers escalation
            if categorization.confidence < 0.70:
                logger.warning(
                    f"⚠️ LOW_CONFIDENCE: CategoryAgent low confidence for {expense_report.expense_id}",
                    extra={
                        "expense_id": expense_report.expense_id,
                        "agent": "CategoryAgent",
                        "confidence": categorization.confidence,
                        "threshold": 0.70,
                        "escalation_trigger": "low_categorization_confidence",
                        "workflow_stage": "confidence_check"
                    }
                )
            
            # Step 2: Parallel processing - PolicyEvaluationAgent and FraudAgent
            logger.info(
                f"⚡ PARALLEL_START: Policy evaluation and fraud assessment for {expense_report.expense_id}",
                extra={
                    "expense_id": expense_report.expense_id,
                    "agents": ["PolicyEvaluationAgent", "FraudAgent"],
                    "workflow_stage": "parallel_processing",
                    "step": 2
                }
            )
            
            # Run policy evaluation and fraud assessment in parallel
            parallel_start_time = workflow.now()
            policy_task = evaluate_policy_compliance(expense_report, categorization)
            fraud_task = assess_fraud_risk(expense_report, categorization)
            
            # Wait for both to complete
            policy_evaluation, fraud_assessment = await workflow.gather(policy_task, fraud_task)
            parallel_duration = (workflow.now() - parallel_start_time).total_seconds()
            
            logger.info(
                f"✅ PARALLEL_COMPLETE: Policy and fraud assessment finished for {expense_report.expense_id}",
                extra={
                    "expense_id": expense_report.expense_id,
                    "agents": ["PolicyEvaluationAgent", "FraudAgent"],
                    "policy_compliant": policy_evaluation.compliant,
                    "policy_confidence": policy_evaluation.confidence,
                    "policy_violations_count": len(policy_evaluation.violations),
                    "fraud_risk": fraud_assessment.overall_risk,
                    "fraud_confidence": fraud_assessment.confidence,
                    "fraud_flags_count": len(fraud_assessment.flags),
                    "duration_seconds": parallel_duration,
                    "workflow_stage": "parallel_complete",
                    "step": 2
                }
            )
            
            # Check confidence levels for escalation
            confidence_issues = []
            if policy_evaluation.confidence < 0.80:
                confidence_issues.append(f"PolicyEvaluationAgent: {policy_evaluation.confidence}")
                logger.warning(
                    f"⚠️ LOW_CONFIDENCE: PolicyEvaluationAgent low confidence for {expense_report.expense_id}",
                    extra={
                        "expense_id": expense_report.expense_id,
                        "agent": "PolicyEvaluationAgent",
                        "confidence": policy_evaluation.confidence,
                        "threshold": 0.80,
                        "escalation_trigger": "low_policy_confidence",
                        "workflow_stage": "confidence_check"
                    }
                )
            
            if fraud_assessment.confidence < 0.65:
                confidence_issues.append(f"FraudAgent: {fraud_assessment.confidence}")
                logger.warning(
                    f"⚠️ LOW_CONFIDENCE: FraudAgent low confidence for {expense_report.expense_id}",
                    extra={
                        "expense_id": expense_report.expense_id,
                        "agent": "FraudAgent",
                        "confidence": fraud_assessment.confidence,
                        "threshold": 0.65,
                        "escalation_trigger": "low_fraud_confidence",
                        "workflow_stage": "confidence_check"
                    }
                )
            
            if confidence_issues:
                logger.info(
                    f"📊 CONFIDENCE_SUMMARY: Multiple confidence issues detected for {expense_report.expense_id}",
                    extra={
                        "expense_id": expense_report.expense_id,
                        "confidence_issues": confidence_issues,
                        "workflow_stage": "confidence_summary"
                    }
                )
            
            # Step 3: DecisionOrchestrationAgent - Make final decision
            logger.info(
                f"🎯 AGENT_START: DecisionOrchestrationAgent processing expense {expense_report.expense_id}",
                extra={
                    "expense_id": expense_report.expense_id,
                    "agent": "DecisionOrchestrationAgent",
                    "workflow_stage": "final_decision",
                    "step": 3,
                    "input_summary": {
                        "category": categorization.category,
                        "category_confidence": categorization.confidence,
                        "policy_compliant": policy_evaluation.compliant,
                        "policy_mandatory_review": policy_evaluation.mandatory_human_review,
                        "fraud_risk": fraud_assessment.overall_risk,
                        "fraud_requires_review": fraud_assessment.requires_human_review
                    }
                }
            )
            
            decision_start_time = workflow.now()
            final_decision = await make_final_decision(
                expense_report, categorization, policy_evaluation, fraud_assessment
            )
            decision_duration = (workflow.now() - decision_start_time).total_seconds()
            
            logger.info(
                f"✅ AGENT_COMPLETE: DecisionOrchestrationAgent finished for expense {expense_report.expense_id}",
                extra={
                    "expense_id": expense_report.expense_id,
                    "agent": "DecisionOrchestrationAgent",
                    "decision": final_decision.decision,
                    "confidence": final_decision.confidence,
                    "is_mandatory_escalation": final_decision.is_mandatory_escalation,
                    "escalation_reason": final_decision.escalation_reason,
                    "duration_seconds": decision_duration,
                    "workflow_stage": "final_decision_complete",
                    "step": 3
                }
            )
            
            # Step 4: Handle decision based on type
            logger.info(
                f"🔀 DECISION_BRANCH: Processing decision '{final_decision.decision}' for {expense_report.expense_id}",
                extra={
                    "expense_id": expense_report.expense_id,
                    "decision": final_decision.decision,
                    "workflow_stage": "decision_routing",
                    "step": 4
                }
            )
            
            if final_decision.decision == "requires_human_review":
                # Escalate to human review
                logger.info(
                    f"👥 HUMAN_ESCALATION: Escalating {expense_report.expense_id} to human review",
                    extra={
                        "expense_id": expense_report.expense_id,
                        "escalation_reason": final_decision.escalation_reason,
                        "is_mandatory": final_decision.is_mandatory_escalation,
                        "workflow_stage": "human_escalation",
                        "decision_path": "requires_human_review"
                    }
                )
                
                self._update_status("under_review", f"Escalated for human review: {final_decision.escalation_reason}")
                
                # Generate response for human reviewer context
                logger.info(
                    f"📝 AGENT_START: ResponseAgent generating escalation context for {expense_report.expense_id}",
                    extra={
                        "expense_id": expense_report.expense_id,
                        "agent": "ResponseAgent",
                        "purpose": "escalation_context",
                        "workflow_stage": "response_generation"
                    }
                )
                
                response = await generate_expense_response(
                    expense_report, categorization, policy_evaluation, final_decision
                )
                
                logger.info(
                    f"✅ AGENT_COMPLETE: ResponseAgent finished escalation context for {expense_report.expense_id}",
                    extra={
                        "expense_id": expense_report.expense_id,
                        "agent": "ResponseAgent",
                        "purpose": "escalation_context",
                        "workflow_stage": "response_generation_complete"
                    }
                )
                
                # Store processing result for human reviewer access
                self._processing_result = ExpenseProcessingResult(
                    expense_report=expense_report,
                    categorization=categorization,
                    policy_evaluation=policy_evaluation,
                    fraud_assessment=fraud_assessment,
                    final_decision=final_decision,
                    expense_response=response,
                    status=self._status
                )
                
                # Wait for human decision with async completion
                logger.info(
                    f"⏳ HUMAN_WAIT: Waiting for human decision on {expense_report.expense_id}",
                    extra={
                        "expense_id": expense_report.expense_id,
                        "timeout_minutes": 30,
                        "workflow_stage": "human_decision_wait"
                    }
                )
                
                human_decision = await self._wait_for_human_decision(expense_report.expense_id)
                
                logger.info(
                    f"👤 HUMAN_DECISION: Human decision received for {expense_report.expense_id}: {human_decision}",
                    extra={
                        "expense_id": expense_report.expense_id,
                        "human_decision": human_decision,
                        "workflow_stage": "human_decision_received"
                    }
                )
                
                # Process human decision
                if human_decision == "APPROVED":
                    logger.info(
                        f"✅ HUMAN_APPROVAL: Human approved expense {expense_report.expense_id}",
                        extra={
                            "expense_id": expense_report.expense_id,
                            "decision_path": "human_approved",
                            "workflow_stage": "human_approval"
                        }
                    )
                    
                    self._update_status("approved", "Approved by human reviewer")
                    
                    # Generate final response for approval
                    await self._generate_approval_response(expense_report, categorization)
                    
                    # Proceed to payment processing
                    logger.info(
                        f"💳 PAYMENT_START: Processing payment for {expense_report.expense_id}",
                        extra={
                            "expense_id": expense_report.expense_id,
                            "amount": str(expense_report.amount),
                            "workflow_stage": "payment_processing"
                        }
                    )
                    
                    await self._process_payment(expense_report.expense_id)
                    self._update_status("paid", "Payment processed successfully")
                    
                    logger.info(
                        f"🎉 WORKFLOW_SUCCESS: Expense {expense_report.expense_id} approved by human and payment processed",
                        extra={
                            "expense_id": expense_report.expense_id,
                            "final_status": "COMPLETED",
                            "decision_path": "human_approved_paid",
                            "workflow_stage": "completion"
                        }
                    )
                    return "COMPLETED"
                else:
                    logger.info(
                        f"❌ HUMAN_REJECTION: Human rejected expense {expense_report.expense_id}",
                        extra={
                            "expense_id": expense_report.expense_id,
                            "rejection_reason": human_decision,
                            "decision_path": "human_rejected",
                            "workflow_stage": "human_rejection"
                        }
                    )
                    
                    self._update_status("final_rejection", f"Rejected by human reviewer: {human_decision}")
                    
                    logger.info(
                        f"🏁 WORKFLOW_END: Expense {expense_report.expense_id} rejected by human reviewer",
                        extra={
                            "expense_id": expense_report.expense_id,
                            "final_status": "REJECTED",
                            "decision_path": "human_rejected",
                            "workflow_stage": "completion"
                        }
                    )
                    return "REJECTED"
            
            elif final_decision.decision == "approved":
                # Auto-approve
                logger.info(
                    f"✅ AUTO_APPROVAL: Auto-approving expense {expense_report.expense_id}",
                    extra={
                        "expense_id": expense_report.expense_id,
                        "decision_confidence": final_decision.confidence,
                        "decision_path": "auto_approved",
                        "workflow_stage": "auto_approval"
                    }
                )
                
                # Generate user response
                logger.info(
                    f"📝 AGENT_START: ResponseAgent generating approval response for {expense_report.expense_id}",
                    extra={
                        "expense_id": expense_report.expense_id,
                        "agent": "ResponseAgent",
                        "purpose": "approval_response",
                        "workflow_stage": "response_generation",
                        "step": 5
                    }
                )
                
                response_start_time = workflow.now()
                response = await generate_expense_response(
                    expense_report, categorization, policy_evaluation, final_decision
                )
                response_duration = (workflow.now() - response_start_time).total_seconds()
                
                logger.info(
                    f"✅ AGENT_COMPLETE: ResponseAgent finished approval response for {expense_report.expense_id}",
                    extra={
                        "expense_id": expense_report.expense_id,
                        "agent": "ResponseAgent",
                        "purpose": "approval_response",
                        "duration_seconds": response_duration,
                        "workflow_stage": "response_generation_complete",
                        "step": 5
                    }
                )
                
                self._update_status("approved", "Automatically approved by AI assessment")
                
                # Store complete processing result
                self._processing_result = ExpenseProcessingResult(
                    expense_report=expense_report,
                    categorization=categorization,
                    policy_evaluation=policy_evaluation,
                    fraud_assessment=fraud_assessment,
                    final_decision=final_decision,
                    expense_response=response,
                    status=self._status
                )
                
                # Process payment
                logger.info(
                    f"💳 PAYMENT_START: Processing payment for auto-approved expense {expense_report.expense_id}",
                    extra={
                        "expense_id": expense_report.expense_id,
                        "amount": str(expense_report.amount),
                        "workflow_stage": "payment_processing"
                    }
                )
                
                await self._process_payment(expense_report.expense_id)
                self._update_status("paid", "Payment processed successfully")
                
                logger.info(
                    f"🎉 WORKFLOW_SUCCESS: Expense {expense_report.expense_id} auto-approved and payment processed",
                    extra={
                        "expense_id": expense_report.expense_id,
                        "final_status": "COMPLETED",
                        "decision_path": "auto_approved_paid",
                        "workflow_stage": "completion"
                    }
                )
                return "COMPLETED"
            
            elif final_decision.decision == "final_rejection":
                # Final rejection
                logger.info(
                    f"❌ FINAL_REJECTION: Final rejection for expense {expense_report.expense_id}",
                    extra={
                        "expense_id": expense_report.expense_id,
                        "decision_confidence": final_decision.confidence,
                        "decision_path": "final_rejection",
                        "workflow_stage": "final_rejection"
                    }
                )
                
                # Generate rejection response
                logger.info(
                    f"📝 AGENT_START: ResponseAgent generating rejection response for {expense_report.expense_id}",
                    extra={
                        "expense_id": expense_report.expense_id,
                        "agent": "ResponseAgent",
                        "purpose": "rejection_response",
                        "workflow_stage": "response_generation",
                        "step": 5
                    }
                )
                
                response = await generate_expense_response(
                    expense_report, categorization, policy_evaluation, final_decision
                )
                
                logger.info(
                    f"✅ AGENT_COMPLETE: ResponseAgent finished rejection response for {expense_report.expense_id}",
                    extra={
                        "expense_id": expense_report.expense_id,
                        "agent": "ResponseAgent",
                        "purpose": "rejection_response",
                        "workflow_stage": "response_generation_complete",
                        "step": 5
                    }
                )
                
                self._update_status("final_rejection", "Rejected due to policy violations")
                
                # Store complete processing result
                self._processing_result = ExpenseProcessingResult(
                    expense_report=expense_report,
                    categorization=categorization,
                    policy_evaluation=policy_evaluation,
                    fraud_assessment=fraud_assessment,
                    final_decision=final_decision,
                    expense_response=response,
                    status=self._status
                )
                
                logger.info(
                    f"🏁 WORKFLOW_END: Expense {expense_report.expense_id} rejected due to policy violations",
                    extra={
                        "expense_id": expense_report.expense_id,
                        "final_status": "REJECTED",
                        "decision_path": "final_rejection",
                        "workflow_stage": "completion"
                    }
                )
                return "REJECTED"
            
            else:  # rejected_with_instructions
                # Rejection with correction instructions
                logger.info(
                    f"📝 REJECTION_WITH_INSTRUCTIONS: Rejecting expense {expense_report.expense_id} with correction instructions",
                    extra={
                        "expense_id": expense_report.expense_id,
                        "decision_confidence": final_decision.confidence,
                        "decision_path": "rejected_with_instructions",
                        "workflow_stage": "rejection_with_instructions"
                    }
                )
                
                # Generate correction instructions response
                logger.info(
                    f"📝 AGENT_START: ResponseAgent generating correction instructions for {expense_report.expense_id}",
                    extra={
                        "expense_id": expense_report.expense_id,
                        "agent": "ResponseAgent",
                        "purpose": "correction_instructions",
                        "workflow_stage": "response_generation",
                        "step": 5
                    }
                )
                
                response = await generate_expense_response(
                    expense_report, categorization, policy_evaluation, final_decision
                )
                
                logger.info(
                    f"✅ AGENT_COMPLETE: ResponseAgent finished correction instructions for {expense_report.expense_id}",
                    extra={
                        "expense_id": expense_report.expense_id,
                        "agent": "ResponseAgent",
                        "purpose": "correction_instructions",
                        "workflow_stage": "response_generation_complete",
                        "step": 5
                    }
                )
                
                self._update_status("rejected_with_instructions", "Rejected - additional information needed")
                
                # Store complete processing result
                self._processing_result = ExpenseProcessingResult(
                    expense_report=expense_report,
                    categorization=categorization,
                    policy_evaluation=policy_evaluation,
                    fraud_assessment=fraud_assessment,
                    final_decision=final_decision,
                    expense_response=response,
                    status=self._status
                )
                
                logger.info(
                    f"🏁 WORKFLOW_END: Expense {expense_report.expense_id} rejected with instructions for resubmission",
                    extra={
                        "expense_id": expense_report.expense_id,
                        "final_status": "REQUIRES_RESUBMISSION",
                        "decision_path": "rejected_with_instructions",
                        "workflow_stage": "completion"
                    }
                )
                return "REQUIRES_RESUBMISSION"
        
        except Exception as e:
            logger.error(
                f"🚨 WORKFLOW_ERROR: Expense processing failed for {expense_report.expense_id}",
                extra={
                    "expense_id": expense_report.expense_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "workflow_stage": "error_handling"
                }
            )
            
            self._update_status("processing_error", f"Processing error: {str(e)}")
            
            # In case of processing error, escalate to human review
            logger.info(
                f"👥 ERROR_ESCALATION: Escalating {expense_report.expense_id} to human review due to processing error",
                extra={
                    "expense_id": expense_report.expense_id,
                    "escalation_reason": "processing_error",
                    "error": str(e),
                    "workflow_stage": "error_escalation"
                }
            )
            
            try:
                human_decision = await self._wait_for_human_decision(expense_report.expense_id)
                
                logger.info(
                    f"👤 ERROR_HUMAN_DECISION: Human decision received after error for {expense_report.expense_id}: {human_decision}",
                    extra={
                        "expense_id": expense_report.expense_id,
                        "human_decision": human_decision,
                        "workflow_stage": "error_human_decision"
                    }
                )
                
                if human_decision == "APPROVED":
                    await self._process_payment(expense_report.expense_id)
                    self._update_status("paid", "Approved after processing error - payment processed")
                    
                    logger.info(
                        f"🎉 ERROR_RECOVERY_SUCCESS: Expense {expense_report.expense_id} approved after error recovery",
                        extra={
                            "expense_id": expense_report.expense_id,
                            "final_status": "COMPLETED",
                            "decision_path": "error_recovery_approved",
                            "workflow_stage": "error_recovery"
                        }
                    )
                    return "COMPLETED"
                else:
                    self._update_status("final_rejection", f"Rejected after processing error: {human_decision}")
                    
                    logger.info(
                        f"❌ ERROR_RECOVERY_REJECTION: Expense {expense_report.expense_id} rejected after error",
                        extra={
                            "expense_id": expense_report.expense_id,
                            "final_status": "REJECTED",
                            "decision_path": "error_recovery_rejected",
                            "workflow_stage": "error_recovery"
                        }
                    )
                    return "REJECTED"
                    
            except Exception as escalation_error:
                logger.error(
                    f"🚨 ESCALATION_FAILURE: Failed to escalate {expense_report.expense_id} after processing error",
                    extra={
                        "expense_id": expense_report.expense_id,
                        "original_error": str(e),
                        "escalation_error": str(escalation_error),
                        "workflow_stage": "escalation_failure"
                    }
                )
                
                self._update_status("failed", "Processing and escalation failed")
                raise ApplicationError(f"Expense processing failed: {str(e)}")
    
    @workflow.query
    def get_status(self) -> ExpenseStatus:
        """Get current expense processing status."""
        return self._status
    
    @workflow.query
    def get_processing_result(self) -> ExpenseProcessingResult:
        """Get complete processing result (for human reviewers)."""
        return self._processing_result
    
    async def _wait_for_human_decision(self, expense_id: str) -> str:
        """
        Wait for human decision using async completion pattern.
        
        Args:
            expense_id: The expense ID
            
        Returns:
            Human decision result
        """
        logger = workflow.logger
        
        try:
            # Use the same async completion pattern as the original expense sample
            # This integrates with the existing expense UI system
            from openai_agents_expense.activities import wait_for_decision_activity
            
            logger.info(
                f"⏳ ACTIVITY_START: Waiting for human decision on {expense_id}",
                extra={
                    "expense_id": expense_id,
                    "activity": "wait_for_decision_activity",
                    "timeout_minutes": 30,
                    "workflow_stage": "human_decision_activity"
                }
            )
            
            # Wait for human decision with extended timeout (30 minutes)
            status = await workflow.execute_activity(
                wait_for_decision_activity,
                expense_id,
                start_to_close_timeout=timedelta(minutes=30),
            )
            
            logger.info(
                f"✅ ACTIVITY_COMPLETE: Human decision activity completed for {expense_id}",
                extra={
                    "expense_id": expense_id,
                    "activity": "wait_for_decision_activity",
                    "decision": status,
                    "workflow_stage": "human_decision_activity_complete"
                }
            )
            
            return status
            
        except Exception as e:
            logger.error(
                f"🚨 ACTIVITY_ERROR: Failed to get human decision for {expense_id}",
                extra={
                    "expense_id": expense_id,
                    "activity": "wait_for_decision_activity",
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "workflow_stage": "human_decision_activity_error"
                }
            )
            # Default to rejection if human decision fails
            return "REJECTED_PROCESSING_ERROR"
    
    async def _process_payment(self, expense_id: str) -> None:
        """
        Process payment for approved expense.
        
        Args:
            expense_id: The expense ID
        """
        logger = workflow.logger
        
        try:
            # Use the existing payment activity from this package (self-contained)
            from openai_agents_expense.activities import payment_activity
            
            logger.info(
                f"💳 ACTIVITY_START: Processing payment for {expense_id}",
                extra={
                    "expense_id": expense_id,
                    "activity": "payment_activity",
                    "timeout_seconds": 30,
                    "workflow_stage": "payment_activity"
                }
            )
            
            await workflow.execute_activity(
                payment_activity,
                expense_id,
                start_to_close_timeout=timedelta(seconds=30),
            )
            
            logger.info(
                f"✅ ACTIVITY_COMPLETE: Payment processing completed for {expense_id}",
                extra={
                    "expense_id": expense_id,
                    "activity": "payment_activity",
                    "workflow_stage": "payment_activity_complete"
                }
            )
            
        except Exception as e:
            logger.error(
                f"🚨 PAYMENT_ERROR: Payment processing failed for {expense_id}",
                extra={
                    "expense_id": expense_id,
                    "activity": "payment_activity",
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "workflow_stage": "payment_error"
                }
            )
            # Don't fail the workflow for payment errors - mark as approved but payment failed
            self._update_status("approved_payment_failed", f"Approved but payment failed: {str(e)}")
    
    async def _generate_approval_response(self, expense_report: ExpenseReport, categorization) -> None:
        """
        Generate approval response after human review.
        
        Args:
            expense_report: The expense report
            categorization: Categorization results
        """
        logger = workflow.logger
        
        logger.info(
            f"📝 APPROVAL_RESPONSE_START: Generating approval response after human review for {expense_report.expense_id}",
            extra={
                "expense_id": expense_report.expense_id,
                "workflow_stage": "post_human_approval_response"
            }
        )
        
        from openai_agents_expense.models import FinalDecision, PolicyEvaluation, PolicyViolation
        
        # Create a simple approval decision for response generation
        approval_decision = FinalDecision(
            decision="approved",
            internal_reasoning="Approved by human reviewer after escalation",
            external_reasoning="Your expense has been approved by our review team",
            escalation_reason=None,
            is_mandatory_escalation=False,
            confidence=1.0
        )
        
        # Create basic policy evaluation for response context
        policy_evaluation = PolicyEvaluation(
            compliant=True,
            violations=[],
            reasoning="Approved by human reviewer",
            requires_human_review=False,
            mandatory_human_review=False,
            policy_explanation="Expense approved through human review process",
            confidence=1.0
        )
        
        # Generate final response
        response = await generate_expense_response(
            expense_report, categorization, policy_evaluation, approval_decision
        )
        
        logger.info(
            f"✅ APPROVAL_RESPONSE_COMPLETE: Approval response generated after human review for {expense_report.expense_id}",
            extra={
                "expense_id": expense_report.expense_id,
                "workflow_stage": "post_human_approval_response_complete"
            }
        )
        
        # Update processing result if it exists
        if self._processing_result:
            self._processing_result.final_decision = approval_decision
            self._processing_result.expense_response = response
    
    def _update_status(self, status: str, message: str) -> None:
        """
        Update expense processing status.
        
        Args:
            status: New status
            message: Status update message
        """
        logger = workflow.logger
        
        previous_status = self._status.current_status
        self._status.current_status = status
        timestamp = workflow.now().strftime('%H:%M:%S')
        status_message = f"{timestamp}: {message}"
        self._status.processing_history.append(status_message)
        self._status.last_updated = workflow.now()
        
        # Set estimated completion based on status
        if status == "under_review":
            self._status.estimated_completion = workflow.now() + timedelta(hours=4)
        elif status in ["approved", "final_rejection", "rejected_with_instructions"]:
            self._status.estimated_completion = workflow.now()
        elif status == "paid":
            self._status.estimated_completion = None
        
        logger.info(
            f"📊 STATUS_UPDATE: Status changed for {self._status.expense_id}",
            extra={
                "expense_id": self._status.expense_id,
                "previous_status": previous_status,
                "new_status": status,
                "status_message": message,
                "workflow_stage": "status_update"
            }
        ) 