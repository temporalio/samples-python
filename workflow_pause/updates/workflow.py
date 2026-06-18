from temporalio import workflow


@workflow.defn
class UpdatePauseWorkflow:
    """Maintains a running total adjusted via updates.

    An update issued against a paused workflow is REJECTED immediately with:
    `Workflow is paused. Cannot update the workflow.` Unpausing lets updates be
    admitted and executed again.
    """

    def __init__(self) -> None:
        self._total = 0
        self._finished = False

    @workflow.run
    async def run(self) -> int:
        await workflow.wait_condition(lambda: self._finished)
        return self._total

    @workflow.update
    async def add(self, amount: int) -> int:
        self._total += amount
        workflow.logger.info("Total is now %d", self._total)
        return self._total

    @workflow.update
    async def finish(self) -> None:
        self._finished = True

    @workflow.query
    def total(self) -> int:
        return self._total
