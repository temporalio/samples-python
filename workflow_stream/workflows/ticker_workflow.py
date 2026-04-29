from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.contrib.workflow_stream import WorkflowStream

from workflow_stream.shared import (
    TOPIC_TICK,
    TickEvent,
    TickerInput,
)


@workflow.defn
class TickerWorkflow:
    """Long-running ticker that bounds its event log via ``truncate``.

    Long-running workflows that publish high volumes of events would
    otherwise grow their event log unboundedly. This workflow shows
    the truncation pattern: every ``truncate_every`` events, drop
    everything except the last ``keep_last`` entries by calling
    ``self.stream.truncate(safe_offset)``.

    Subscribers that fall behind a truncation jump forward to the new
    base offset transparently (the iterator handles the
    ``TruncatedOffset`` error internally), so consumers stay live but
    may not see every intermediate event. That is the trade: bounded
    log size in exchange for at-best-effort delivery to slow
    consumers.

    To compute the truncation offset the workflow tracks its own
    published count. ``WorkflowStream`` does not expose a workflow-side
    head-offset accessor, but the running count plus the carried
    ``base_offset`` (in continue-as-new chains) is sufficient.
    """

    @workflow.init
    def __init__(self, input: TickerInput) -> None:
        self.stream = WorkflowStream(prior_state=input.stream_state)
        # Running count of events published by THIS run. To compute a
        # global offset, add the prior_state's base_offset (omitted
        # here — this sample doesn't continue-as-new).
        self._published = 0

    @workflow.run
    async def run(self, input: TickerInput) -> str:
        for n in range(input.count):
            self.stream.publish(TOPIC_TICK, TickEvent(n=n))
            self._published += 1
            await workflow.sleep(timedelta(milliseconds=input.interval_ms))
            if (
                self._published % input.truncate_every == 0
                and self._published > input.keep_last
            ):
                # Drop everything except the last `keep_last` entries.
                truncate_to = self._published - input.keep_last
                self.stream.truncate(truncate_to)
        return f"ticker emitted {self._published} events"
