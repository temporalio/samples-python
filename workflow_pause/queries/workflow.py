from datetime import timedelta

from temporalio import workflow


@workflow.defn
class QueryPauseWorkflow:
    """A loop exposing its progress via a query.

    Queries succeed while the workflow is running, but are REJECTED while it is
    paused with: `query was rejected, workflow has status: Paused`. Unpausing
    makes the workflow queryable again.
    """

    def __init__(self) -> None:
        self._count = 0

    @workflow.run
    async def run(self, iterations: int) -> int:
        for _ in range(iterations):
            await workflow.sleep(timedelta(seconds=3))
            self._count += 1
        return self._count

    @workflow.query
    def current_count(self) -> int:
        return self._count
