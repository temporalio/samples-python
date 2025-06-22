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
    from openai_agents_expense.agents.category_agent import categorize_expense
    from openai_agents_expense.agents.policy_evaluation_agent import evaluate_policy_compliance
    from openai_agents_expense.agents.fraud_agent import assess_fraud_risk
    from openai_agents_expense.agents.decision_orchestration_agent import make_final_decision
    from openai_agents_expense.agents.response_agent import generate_expense_response


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
            last_updated=datetime.now(),
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
        logger.info(f"Starting expense processing for {expense_report.expense_id}")
        
        # Initialize status tracking
        self._status.expense_id = expense_report.expense_id
        self._update_status("processing", "AI agents processing expense report")
        
        try:
            # Step 1: CategoryAgent - Categorize expense and validate vendor
            logger.info(f"Step 1: Categorizing expense {expense_report.expense_id}")
            categorization = await categorize_expense(expense_report)
            
            # Check if categorization confidence triggers escalation
            if categorization.confidence < 0.70:
                logger.warning(f"Low categorization confidence ({categorization.confidence}) for {expense_report.expense_id}")
            
            # Step 2: Parallel processing - PolicyEvaluationAgent and FraudAgent
            logger.info(f"Step 2: Parallel policy evaluation and fraud assessment for {expense_report.expense_id}")
            
            # Run policy evaluation and fraud assessment in parallel
            policy_task = evaluate_policy_compliance(expense_report, categorization)
            fraud_task = assess_fraud_risk(expense_report, categorization)
            
            # Wait for both to complete
            policy_evaluation, fraud_assessment = await workflow.gather(policy_task, fraud_task)
            
            # Check confidence levels for escalation
            if policy_evaluation.confidence < 0.80:
                logger.warning(f"Low policy evaluation confidence ({policy_evaluation.confidence}) for {expense_report.expense_id}")
            
            if fraud_assessment.confidence < 0.65:
                logger.warning(f"Low fraud assessment confidence ({fraud_assessment.confidence}) for {expense_report.expense_id}")
            
            # Step 3: DecisionOrchestrationAgent - Make final decision
            logger.info(f"Step 3: Making final decision for {expense_report.expense_id}")
            final_decision = await make_final_decision(
                expense_report, categorization, policy_evaluation, fraud_assessment
            )
            
            # Step 4: Handle decision based on type
            if final_decision.decision == "requires_human_review":
                # Escalate to human review
                logger.info(f"Escalating {expense_report.expense_id} to human review: {final_decision.escalation_reason}")
                
                self._update_status("under_review", f"Escalated for human review: {final_decision.escalation_reason}")
                
                # Store processing result for human reviewer access
                response = await generate_expense_response(
                    expense_report, categorization, policy_evaluation, final_decision
                )
                
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
                human_decision = await self._wait_for_human_decision(expense_report.expense_id)
                
                # Process human decision
                if human_decision == "APPROVED":
                    self._update_status("approved", "Approved by human reviewer")
                    
                    # Generate final response for approval
                    final_response = await self._generate_approval_response(expense_report, categorization)
                    
                    # Proceed to payment processing
                    await self._process_payment(expense_report.expense_id)
                    self._update_status("paid", "Payment processed successfully")
                    
                    logger.info(f"Expense {expense_report.expense_id} approved by human and payment processed")
                    return "COMPLETED"
                else:
                    self._update_status("final_rejection", f"Rejected by human reviewer: {human_decision}")
                    logger.info(f"Expense {expense_report.expense_id} rejected by human reviewer")
                    return "REJECTED"
            
            elif final_decision.decision == "approved":
                # Auto-approve
                logger.info(f"Auto-approving expense {expense_report.expense_id}")
                
                # Step 5: ResponseAgent - Generate user response
                response = await generate_expense_response(
                    expense_report, categorization, policy_evaluation, final_decision
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
                await self._process_payment(expense_report.expense_id)
                self._update_status("paid", "Payment processed successfully")
                
                logger.info(f"Expense {expense_report.expense_id} auto-approved and payment processed")
                return "COMPLETED"
            
            elif final_decision.decision == "final_rejection":
                # Final rejection
                logger.info(f"Final rejection for expense {expense_report.expense_id}")
                
                response = await generate_expense_response(
                    expense_report, categorization, policy_evaluation, final_decision
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
                
                logger.info(f"Expense {expense_report.expense_id} rejected due to policy violations")
                return "REJECTED"
            
            else:  # rejected_with_instructions
                # Rejection with correction instructions
                logger.info(f"Rejecting expense {expense_report.expense_id} with correction instructions")
                
                response = await generate_expense_response(
                    expense_report, categorization, policy_evaluation, final_decision
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
                
                logger.info(f"Expense {expense_report.expense_id} rejected with instructions for resubmission")
                return "REQUIRES_RESUBMISSION"
        
        except Exception as e:
            logger.error(f"Expense processing failed for {expense_report.expense_id}: {e}")
            self._update_status("processing_error", f"Processing error: {str(e)}")
            
            # In case of processing error, escalate to human review
            logger.info(f"Escalating {expense_report.expense_id} to human review due to processing error")
            
            try:
                human_decision = await self._wait_for_human_decision(expense_report.expense_id)
                
                if human_decision == "APPROVED":
                    await self._process_payment(expense_report.expense_id)
                    self._update_status("paid", "Approved after processing error - payment processed")
                    return "COMPLETED"
                else:
                    self._update_status("final_rejection", f"Rejected after processing error: {human_decision}")
                    return "REJECTED"
                    
            except Exception as escalation_error:
                logger.error(f"Failed to escalate {expense_report.expense_id}: {escalation_error}")
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
            from expense.activities import wait_for_decision_activity
            
            # Wait for human decision with extended timeout (30 minutes)
            status = await workflow.execute_activity(
                wait_for_decision_activity,
                expense_id,
                start_to_close_timeout=timedelta(minutes=30),
            )
            
            logger.info(f"Human decision received for {expense_id}: {status}")
            return status
            
        except Exception as e:
            logger.error(f"Failed to get human decision for {expense_id}: {e}")
            # Default to rejection if human decision fails
            return "REJECTED_PROCESSING_ERROR"
    
    async def _process_payment(self, expense_id: str) -> None:
        """
        Process payment for approved expense.
        
        Args:
            expense_id: The expense ID
        """
        try:
            # Use the existing payment activity from the original expense sample
            from expense.activities import payment_activity
            
            await workflow.execute_activity(
                payment_activity,
                expense_id,
                start_to_close_timeout=timedelta(seconds=30),
            )
            
        except Exception as e:
            logger = workflow.logger
            logger.error(f"Payment processing failed for {expense_id}: {e}")
            # Don't fail the workflow for payment errors - mark as approved but payment failed
            self._update_status("approved_payment_failed", f"Approved but payment failed: {str(e)}")
    
    async def _generate_approval_response(self, expense_report: ExpenseReport, categorization) -> None:
        """
        Generate approval response after human review.
        
        Args:
            expense_report: The expense report
            categorization: Categorization results
        """
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
        self._status.current_status = status
        self._status.processing_history.append(f"{datetime.now().strftime('%H:%M:%S')}: {message}")
        self._status.last_updated = datetime.now()
        
        # Set estimated completion based on status
        if status == "under_review":
            self._status.estimated_completion = datetime.now() + timedelta(hours=4)
        elif status in ["approved", "final_rejection", "rejected_with_instructions"]:
            self._status.estimated_completion = datetime.now()
        elif status == "paid":
            self._status.estimated_completion = None 