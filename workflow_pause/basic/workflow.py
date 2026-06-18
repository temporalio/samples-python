from datetime import timedelta

from temporalio import workflow


@workflow.defn
class BasicPauseWorkflow:
    """A loop that logs progress and sleeps on a timer each iteration.

    While the workflow is paused, no workflow tasks are dispatched, so the
    timer does not advance and the iteration count stops moving. Unpausing
    lets it resume from where it left off.
    """

    def __init__(self) -> None:
        self._completed = 0

    @workflow.run
    async def run(self, iterations: int) -> int:
        for i in range(iterations):
            workflow.logger.info("Starting iteration %d of %d", i + 1, iterations)
            await workflow.sleep(timedelta(seconds=3))
            self._completed += 1
            workflow.logger.info("Completed iteration %d of %d", i + 1, iterations)
        return self._completed

    @workflow.query
    def completed(self) -> int:
        return self._completed
