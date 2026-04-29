from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.contrib.workflow_stream import WorkflowStream

from workflow_stream.shared import (
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
            self.stream.publish(TOPIC_STATUS, StageEvent(stage=stage))
            if stage != "complete":
                await workflow.sleep(timedelta(seconds=2))
        return f"pipeline {input.pipeline_id} done"
