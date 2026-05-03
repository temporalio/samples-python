from __future__ import annotations

from dataclasses import dataclass

from temporalio.contrib.workflow_streams import WorkflowStreamState

TASK_QUEUE = "workflow-stream-sample-task-queue"

# Topics published by the workflow / activity.
TOPIC_STATUS = "status"
TOPIC_PROGRESS = "progress"
TOPIC_NEWS = "news"
TOPIC_TICK = "tick"


@dataclass
class OrderInput:
    order_id: str
    # Carries stream state across continue-as-new. None on a fresh start.
    stream_state: WorkflowStreamState | None = None


@dataclass
class StatusEvent:
    kind: str
    order_id: str


@dataclass
class ProgressEvent:
    message: str


@dataclass
class PipelineInput:
    pipeline_id: str
    # Carries stream state across continue-as-new. None on a fresh start.
    stream_state: WorkflowStreamState | None = None


@dataclass
class StageEvent:
    stage: str


@dataclass
class HubInput:
    hub_id: str
    # Carries stream state across continue-as-new. None on a fresh start.
    stream_state: WorkflowStreamState | None = None


@dataclass
class NewsEvent:
    headline: str


@dataclass
class TickerInput:
    count: int = 20
    keep_last: int = 3
    truncate_every: int = 5
    interval_ms: int = 400
    # Carries stream state across continue-as-new. None on a fresh start.
    stream_state: WorkflowStreamState | None = None


@dataclass
class TickEvent:
    n: int
