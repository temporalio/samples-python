import asyncio
from datetime import timedelta

from temporalio import workflow


@workflow.defn
class CancelTerminatePauseWorkflow:
    """A loop that runs cleanup logic when cancelled.

    On a PAUSED workflow:
      - `temporal workflow terminate` takes effect immediately.
      - `temporal workflow cancel` records a WorkflowExecutionCancelRequested
        event, but the workflow stays Paused and its cancellation handling (the
        cleanup below) does not run until the workflow is unpaused.
    """

    @workflow.run
    async def run(self, iterations: int) -> str:
        try:
            for i in range(iterations):
                workflow.logger.info("Working, iteration %d", i + 1)
                await workflow.sleep(timedelta(seconds=3))
            return "completed"
        except asyncio.CancelledError:
            workflow.logger.info("Cancellation received — running cleanup")
            raise
