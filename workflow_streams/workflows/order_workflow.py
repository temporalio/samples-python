from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.contrib.workflow_streams import WorkflowStream

from workflow_streams.shared import (
    TOPIC_PROGRESS,
    TOPIC_STATUS,
    OrderInput,
    ProgressEvent,
    StatusEvent,
)

with workflow.unsafe.imports_passed_through():
    from workflow_streams.activities.payment_activity import charge_card


@workflow.defn
class OrderWorkflow:
    """Process a fake order, publishing status and progress events.

    The workflow itself publishes status changes; an activity it runs
    publishes finer-grained progress events using a
    `WorkflowStreamClient`. A single stream carries both topics —
    subscribers can filter on the topic(s) they care about.
    """

    @workflow.init
    def __init__(self, input: OrderInput) -> None:
        # Construct the stream from @workflow.init so it can register
        # signal/update/query handlers before the workflow accepts any
        # messages. Threading prior_state lets the workflow survive
        # continue-as-new without losing buffered items.
        self.stream = WorkflowStream(prior_state=input.stream_state)
        self.status = self.stream.topic(TOPIC_STATUS, type=StatusEvent)
        self.progress = self.stream.topic(TOPIC_PROGRESS, type=ProgressEvent)

    @workflow.run
    async def run(self, input: OrderInput) -> str:
        self.status.publish(StatusEvent(kind="received", order_id=input.order_id))

        charge_id = await workflow.execute_activity(
            charge_card,
            input.order_id,
            start_to_close_timeout=timedelta(seconds=30),
        )

        self.status.publish(StatusEvent(kind="shipped", order_id=input.order_id))
        self.progress.publish(ProgressEvent(message=f"charge id: {charge_id}"))
        self.status.publish(StatusEvent(kind="complete", order_id=input.order_id))
        # The "complete" status event above is the in-band terminator
        # subscribers break on (see run_publisher.py). Hold the run
        # open briefly so subscribers' next poll delivers it before
        # this task returns and the in-memory log is gone.
        await workflow.sleep(timedelta(milliseconds=500))
        return charge_id
