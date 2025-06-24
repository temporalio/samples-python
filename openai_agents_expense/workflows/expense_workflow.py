"""
Main ExpenseWorkflow - Orchestrates AI agents for expense processing with enhanced decision-making.

This workflow coordinates:
1. CategoryAgent (categorization and vendor validation)
2. PolicyEvaluationAgent and FraudAgent (parallel processing)
3. DecisionOrchestrationAgent (final decision making)
4. ResponseAgent (user communication)
5. Human-in-the-loop integration for escalated cases
"""

import asyncio
import traceback
from datetime import timedelta
from typing import Optional

from temporalio import workflow

# Import models at module level (safe for workflows)
from openai_agents_expense.ai_agents.decision_orchestration_agent import (
    create_decision_orchestration_agent,
)
#TODO - not really necessary to pass these through but seeing if it helps with sandboxing issues
with workflow.unsafe.imports_passed_through():
    from openai_agents_expense.models import (
        AgentDecision,
        AgentDecisionInput,
        ExpenseCategory,
        ExpenseProcessingResult,
        ExpenseReport,
        ExpenseResponse,
        ExpenseResponseInput,
        ExpenseStatus,
        ExpenseStatusEnum,
        FraudAssessment,
        FraudAssessmentInput,
        PolicyEvaluation,
        PolicyEvaluationInput,
        PolicyViolation,
        UpdateExpenseActivityInput
    )

# Import activities and agent functions
with workflow.unsafe.imports_passed_through():
    from agents import Runner

    from openai_agents_expense.activities import (
        UpdateExpenseActivityInput,
        create_expense_activity,
        payment_activity,
        update_expense_activity,
        wait_for_decision_activity,
    )
    from openai_agents_expense.ai_agents.category_agent import create_category_agent
    from openai_agents_expense.ai_agents.fraud_agent import create_fraud_agent
    from openai_agents_expense.ai_agents.policy_evaluation_agent import (
        create_policy_evaluation_agent,
    )
    from openai_agents_expense.ai_agents.response_agent import create_response_agent


@workflow.defn(sandboxed=False)
class ExpenseWorkflow:
    """
    Main expense processing workflow with OpenAI Agents integration.
    """

    def __init__(self):
        self._status = ExpenseStatus(
            current_status=ExpenseStatusEnum.SUBMITTED,
            last_updated=workflow.now(),
        )
        self._processing_result: Optional[ExpenseProcessingResult] = None

    def _update_status(self, status: ExpenseStatusEnum) -> None:
        """Update expense processing status."""
        self._status.current_status = status
        self._status.last_updated = workflow.now()
        # workflow.logger.info(f"📊 STATUS_UPDATE: {self._status.current_status} → {status}")

    @workflow.run
    async def run(self, expense_report: ExpenseReport) -> str:
        """
        Process an expense report using AI agents.

        Args:
            expense_report: The expense report to process

        Returns:
            Final status of the expense processing
        """

        workflow.logger.info(
            f"🚀 WORKFLOW_START: Processing expense {expense_report.expense_id}"
        )

        # Initialize status tracking
        self._update_status(ExpenseStatusEnum.PROCESSING)

        # try:
        # Step 0: Create expense in server
        workflow.logger.info(
            f"🏗️ EXPENSE_CREATION: Creating expense entry for {expense_report.expense_id}"
        )
        await workflow.execute_activity(
            create_expense_activity,
            expense_report,
            start_to_close_timeout=timedelta(seconds=30),
        )
        workflow.logger.info(f"✅ EXPENSE_CREATED: {expense_report.expense_id}")

        # Step 1: CategoryAgent - Categorize expense and validate vendor
        workflow.logger.info(
            f"📋 AGENT_START: CategoryAgent processing {expense_report.expense_id}"
        )
        category_result = await Runner.run(
            create_category_agent(), input=expense_report.model_dump_json()
        )
        categorization: ExpenseCategory = category_result.final_output

        # TODO: why is this needed?
        categorization = ExpenseCategory.model_validate(categorization.model_dump())
        workflow.logger.info(
            f"✅ AGENT_COMPLETE: CategoryAgent finished | categorization={categorization} >>> {type(categorization)} >>> {categorization.model_dump_json()}"
        )

        # Step 2: Parallel processing - PolicyEvaluationAgent and FraudAgent
        workflow.logger.info(
            f"⚡ PARALLEL_START: Policy evaluation and fraud assessment for {expense_report.expense_id}"
        )

        policy_result, fraud_result = await asyncio.gather(
            Runner.run(
                create_policy_evaluation_agent(),
                input=PolicyEvaluationInput(
                    expense_report=expense_report,
                    categorization=categorization,
                ).model_dump_json(),
            ),
            Runner.run(
                create_fraud_agent(),
                input=FraudAssessmentInput(
                    expense_report=expense_report,
                    categorization=categorization,
                ).model_dump_json(),
            ),
        )
        policy_evaluation = PolicyEvaluation.model_validate(
            policy_result.final_output.model_dump()
        )
        fraud_assessment = FraudAssessment.model_validate(
            fraud_result.final_output.model_dump()
        )
        workflow.logger.info(
            f"✅ PARALLEL_COMPLETE: Policy and fraud assessment finished | policy_evaluation={policy_evaluation} | fraud_assessment={fraud_assessment}"
        )

        # Step 3: DecisionOrchestrationAgent - Make final decision
        workflow.logger.info(
            f"🎯 AGENT_START: DecisionOrchestrationAgent processing {expense_report.expense_id}"
        )

        agent_decision_result = await Runner.run(
            create_decision_orchestration_agent(),
            input=AgentDecisionInput(
                expense_report=expense_report,
                categorization=categorization,
                policy_evaluation=policy_evaluation,
                fraud_assessment=fraud_assessment,
            ).model_dump_json(),
        )
        agent_decision = AgentDecision.model_validate(
            agent_decision_result.final_output.model_dump()
        )
        workflow.logger.info(
            f"✅ AGENT_COMPLETE: DecisionOrchestrationAgent finished | agent_decision={agent_decision}"
        )

        # Update the expense state in the UI server
        # expense_processing_result = ExpenseProcessingResult(
        #     expense_report=expense_report,
        #     categorization=categorization,
        #     policy_evaluation=policy_evaluation,
        #     fraud_assessment=fraud_assessment,
        #     agent_decision=agent_decision,
        # )
        # expense_processing_result = ExpenseProcessingResult.model_validate(expense_processing_result.model_dump())
        update_expense_activity_input = UpdateExpenseActivityInput(
            expense_id=expense_report.expense_id,
            expense_report=expense_report,
            categorization=categorization,
            policy_evaluation=policy_evaluation,
            fraud_assessment=fraud_assessment,
            agent_decision=agent_decision,
        )
        await workflow.execute_activity(
            update_expense_activity,
            update_expense_activity_input,
            start_to_close_timeout=timedelta(seconds=30),
        )

        # Get human approval if needed
        if agent_decision.decision == "requires_human_review":
            await self._handle_human_review(expense_report.expense_id)
        final_decision = self._status.current_status

        # Generate the response for the end-user
        response = await Runner.run(
            create_response_agent(),
            input=ExpenseResponseInput(
                expense_report=expense_report,
                categorization=categorization,
                policy_evaluation=policy_evaluation,
                agent_decision=agent_decision,
                final_decision=final_decision,
            ).model_dump_json(),
        )
        expense_response: ExpenseResponse = ExpenseResponse.model_validate(
            response.final_output.model_dump()
        )

        # Store the final processing result
        self._processing_result = ExpenseProcessingResult(
            expense_report=expense_report,
            categorization=categorization,
            policy_evaluation=policy_evaluation,
            fraud_assessment=fraud_assessment,
            agent_decision=agent_decision,
            expense_response=expense_response,
            final_decision=final_decision,
        )

        # Make payment if needed
        if final_decision == ExpenseStatusEnum.APPROVED:
            await self._process_payment(expense_report.expense_id)
            self._update_status(ExpenseStatusEnum.PAID)

        workflow.logger.info(
            f"🏁🏁🏁 WORKFLOW_END: {expense_report.expense_id} completed with final decision {final_decision} and decision summary: {expense_response.decision_summary}"
        )
        return expense_response.decision_summary

    async def _process_decision(
        self,
        expense_report: ExpenseReport,
        categorization: ExpenseCategory,
        policy_evaluation: PolicyEvaluation,
        fraud_assessment: FraudAssessment,
        agent_decision: AgentDecision,
    ) -> str:
        """Process the final decision and return workflow result."""
        workflow.logger.info(
            f"🔀 DECISION_BRANCH: Processing '{agent_decision.decision}' for {expense_report.expense_id}"
        )

        if agent_decision.decision == "requires_human_review":
            return await self._handle_human_review(expense_report.expense_id)

        elif agent_decision.decision == "approved":
            return await self._handle_auto_approval(
                expense_report,
                categorization,
                policy_evaluation,
                fraud_assessment,
                agent_decision,
            )

        elif agent_decision.decision == "final_rejection":
            return await self._handle_final_rejection(
                expense_report,
                categorization,
                policy_evaluation,
                fraud_assessment,
                agent_decision,
            )

        else:  # rejected_with_instructions
            return await self._handle_rejection_with_instructions(
                expense_report,
                categorization,
                policy_evaluation,
                fraud_assessment,
                agent_decision,
            )

    async def _handle_human_review(
        self,
        expense_id: str,
    ) -> str:
        """Handle human review escalation."""
        workflow.logger.info(
            f"👥 HUMAN_ESCALATION: Escalating {expense_id} to human review"
        )

        self._update_status(ExpenseStatusEnum.MANAGER_REVIEW)

        # Wait for human decision
        workflow.logger.info(
            f"⏳ HUMAN_WAIT: Waiting for human decision on {expense_id}"
        )
        human_decision = await workflow.execute_activity(
                wait_for_decision_activity,
                expense_id,
                start_to_close_timeout=timedelta(minutes=30),
            )
        workflow.logger.info(
            f"👤 HUMAN_DECISION: {human_decision} for {expense_id}"
        )

        #TODO - make these codes constants
        if human_decision == "APPROVED":
            self._update_status(ExpenseStatusEnum.APPROVED)
            workflow.logger.info(
                f"🎉 WORKFLOW_SUCCESS: {expense_id} approved by human and paid"
            )
            return "COMPLETED"
        else:
            self._update_status(ExpenseStatusEnum.FINAL_REJECTION)
            workflow.logger.info(
                f"🏁 WORKFLOW_END: {expense_id} rejected by human reviewer"
            )
            return "REJECTED"

    async def _generate_response(
        self,
        expense_report: ExpenseReport,
        categorization: ExpenseCategory,
        policy_evaluation: PolicyEvaluation,
        agent_decision: AgentDecision,
    ) -> ExpenseResponse:
        """Generate response using ResponseAgent."""
        logger = workflow.logger
        workflow.logger.info(
            f"📝 AGENT_START: ResponseAgent generating response for {expense_report.expense_id}"
        )

        # Ensure proper serialization for Pydantic models
        response_input = ExpenseResponseInput(
            expense_report=expense_report,
            categorization=ExpenseCategory.model_validate(categorization.model_dump()),
            policy_evaluation=PolicyEvaluation.model_validate(
                policy_evaluation.model_dump()
            ),
            agent_decision=AgentDecision.model_validate(agent_decision.model_dump()),
        )

        response = await Runner.run(
            create_response_agent(),
            input=response_input.model_dump_json(),
        )

        expense_response = ExpenseResponse.model_validate(response.final_output.model_dump())
        workflow.logger.info(
            f"✅ AGENT_COMPLETE: ResponseAgent finished | response={expense_response}"
        )
        return expense_response

    @workflow.query
    def get_status(self) -> ExpenseStatus:
        """Get current expense processing status."""
        return self._status

    @workflow.query
    def get_processing_result(self) -> Optional[ExpenseProcessingResult]:
        """Get complete processing result."""
        return self._processing_result


    async def _process_payment(self, expense_id: str) -> None:
        """Process payment for approved expense."""
        workflow.logger.info(f"💳 ACTIVITY_START: Processing payment for {expense_id}")

        try:
            await workflow.execute_activity(
                payment_activity,
                expense_id,
                start_to_close_timeout=timedelta(seconds=30),
            )
            workflow.logger.info(
                f"✅ ACTIVITY_COMPLETE: Payment processing completed for {expense_id}"
            )

        except Exception as e:
            workflow.logger.error(
                f"🚨 PAYMENT_ERROR: Payment processing failed for {expense_id} | error={str(e)} | error_type={type(e).__name__} | traceback={traceback.format_exc()}"
            )
            # Note: We need to define additional status enum values for payment error states
            # self._update_status("approved_payment_failed", f"Approved but payment failed: {str(e)}")

    async def _handle_auto_approval(
        self,
        expense_report: ExpenseReport,
        categorization: ExpenseCategory,
        policy_evaluation: PolicyEvaluation,
        fraud_assessment: FraudAssessment,
        agent_decision: AgentDecision,
    ) -> str:
        """Handle auto-approved expenses."""
        workflow.logger.info(
            f"✅ AUTO_APPROVAL: Processing auto-approved expense {expense_report.expense_id}"
        )
        
        self._update_status(ExpenseStatusEnum.APPROVED)
        
        # Process payment
        await self._process_payment(expense_report.expense_id)
        self._update_status(ExpenseStatusEnum.PAID)
        
        return "APPROVED"

    async def _handle_final_rejection(
        self,
        expense_report: ExpenseReport,
        categorization: ExpenseCategory,
        policy_evaluation: PolicyEvaluation,
        fraud_assessment: FraudAssessment,
        agent_decision: AgentDecision,
    ) -> str:
        """Handle finally rejected expenses."""
        workflow.logger.info(
            f"❌ FINAL_REJECTION: Processing final rejection for expense {expense_report.expense_id}"
        )
        
        self._update_status(ExpenseStatusEnum.FINAL_REJECTION)
        
        return "REJECTED"

    async def _handle_rejection_with_instructions(
        self,
        expense_report: ExpenseReport,
        categorization: ExpenseCategory,
        policy_evaluation: PolicyEvaluation,
        fraud_assessment: FraudAssessment,
        agent_decision: AgentDecision,
    ) -> str:
        """Handle rejection with instructions for resubmission."""
        workflow.logger.info(
            f"📋 REJECTION_WITH_INSTRUCTIONS: Processing rejection with instructions for expense {expense_report.expense_id}"
        )
        
        self._update_status(ExpenseStatusEnum.REJECTED_WITH_INSTRUCTIONS)
        
        return "REJECTED_WITH_INSTRUCTIONS"
