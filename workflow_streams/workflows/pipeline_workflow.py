from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.contrib.workflow_streams import WorkflowStream

from workflow_streams.shared import (
    TOPIC_STATUS,
    PipelineInput,
    StageEvent,
)


@workflow.defn
class PipelineWorkflow:
    """Multi-stage pipeline that publishes stage transitions over time.

    Stages are spaced out with ``workflow.sleep`` so a subscriber can
    realistically disconnect partway through and reconnect without the
    pipeline finishing in the meantime — the shape needed to demo the
    "show up late and still see what happened" pattern.
    """

    @workflow.init
    def __init__(self, input: PipelineInput) -> None:
        self.stream = WorkflowStream(prior_state=input.stream_state)
        self.status = self.stream.topic(TOPIC_STATUS, type=StageEvent)

    @workflow.run
    async def run(self, input: PipelineInput) -> str:
        stages = [
            "validating",
            "loading data",
            "transforming",
            "writing output",
            "verifying",
            "complete",
        ]
        for stage in stages:
            self.status.publish(StageEvent(stage=stage))
            if stage != "complete":
                await workflow.sleep(timedelta(seconds=2))
        # The "complete" stage above is the in-band terminator
        # subscribers break on. Hold the run open briefly so the final
        # poll delivers it.
        await workflow.sleep(timedelta(milliseconds=500))
        return f"pipeline {input.pipeline_id} done"
