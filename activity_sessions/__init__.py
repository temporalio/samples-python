from dataclasses import dataclass

TASK_QUEUE = "activity-session-cache"


@dataclass(frozen=True)
class StepEvent:
    """Sent by an activity when a step starts and again when it finishes."""

    workflow_id: str
    step: int
    worker: str
    cache_hit: bool
    finished: bool
