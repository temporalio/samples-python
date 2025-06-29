from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from expense.activities import (
        create_expense_activity,
        payment_activity,
        register_for_decision_activity,
    )


@workflow.defn
class SampleExpenseWorkflow:
    def __init__(self) -> None:
        self.expense_decision: str = ""

    @workflow.signal
    async def expense_decision_signal(self, decision: str) -> None:
        """Signal handler for expense decision."""
        self.expense_decision = decision

    @workflow.run
    async def run(self, expense_id: str) -> str:
        logger = workflow.logger

        # Step 1: Create new expense report
        try:
            await workflow.execute_activity(
                create_expense_activity,
                expense_id,
                start_to_close_timeout=timedelta(seconds=10),
            )
        except Exception as err:
            logger.exception(f"Failed to create expense report: {err}")
            raise

        # Step 2: Register for decision and wait for signal
        try:
            await workflow.execute_activity(
                register_for_decision_activity,
                expense_id,
                start_to_close_timeout=timedelta(seconds=10),
            )
        except Exception as err:
            logger.exception(f"Failed to register for decision: {err}")
            raise

        # Wait for the expense decision signal with a timeout
        logger.info(f"Waiting for expense decision signal for {expense_id}")
        await workflow.wait_condition(
            lambda: self.expense_decision != "", timeout=timedelta(minutes=10)
        )

        status = self.expense_decision
        if status != "APPROVED":
            logger.info(f"Workflow completed. ExpenseStatus: {status}")
            return ""

        # Step 3: Request payment for the expense
        try:
            await workflow.execute_activity(
                payment_activity,
                expense_id,
                start_to_close_timeout=timedelta(seconds=10),
            )
        except Exception as err:
            logger.info(f"Workflow completed with payment failed. Error: {err}")
            raise

        logger.info("Workflow completed with expense payment completed.")
        return "COMPLETED"
