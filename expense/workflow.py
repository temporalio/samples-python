from datetime import timedelta

from temporalio import workflow


@workflow.defn
class SampleExpenseWorkflow:
    @workflow.run
    async def run(self, expense_id: str) -> str:
        logger = workflow.logger
        
        # Step 1: Create new expense report
        try:
            await workflow.execute_activity(
                "create_expense_activity",
                expense_id,
                start_to_close_timeout=timedelta(seconds=10),
            )
        except Exception as err:
            logger.error(f"Failed to create expense report: {err}")
            raise

        # Step 2: Wait for the expense report to be approved (or rejected)
        # Notice that we set the timeout to be 10 minutes for this sample demo. If the expected time for the activity to
        # complete (waiting for human to approve the request) is longer, you should set the timeout accordingly so the
        # Temporal system will wait accordingly. Otherwise, Temporal system could mark the activity as failure by timeout.
        status = await workflow.execute_activity(
            "wait_for_decision_activity",
            expense_id,
            start_to_close_timeout=timedelta(minutes=10),
        )

        if status != "APPROVED":
            logger.info(f"Workflow completed. ExpenseStatus: {status}")
            return ""

        # Step 3: Request payment for the expense
        try:
            await workflow.execute_activity(
                "payment_activity",
                expense_id,
                start_to_close_timeout=timedelta(seconds=10),
            )
        except Exception as err:
            logger.info(f"Workflow completed with payment failed. Error: {err}")
            raise

        logger.info("Workflow completed with expense payment completed.")
        return "COMPLETED" 