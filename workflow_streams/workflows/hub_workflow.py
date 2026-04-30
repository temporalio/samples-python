from __future__ import annotations

from temporalio import workflow
from temporalio.contrib.workflow_streams import WorkflowStream

from workflow_streams.shared import HubInput


@workflow.defn
class HubWorkflow:
    """Passive stream host: starts up, waits, closes when told.

    Unlike OrderWorkflow or PipelineWorkflow, this workflow does no
    work of its own — it exists only to host a ``WorkflowStream`` that
    external publishers push events into and external subscribers read
    from. The shape that fits a backend service or "event bus" pattern,
    where the workflow owns durable state but the events come from
    outside.
    """

    @workflow.init
    def __init__(self, input: HubInput) -> None:
        self.stream = WorkflowStream(prior_state=input.stream_state)
        self._closed = False

    @workflow.run
    async def run(self, input: HubInput) -> str:
        await workflow.wait_condition(lambda: self._closed)
        return f"hub {input.hub_id} closed"

    @workflow.signal
    def close(self) -> None:
        self._closed = True
