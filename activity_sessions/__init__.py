from dataclasses import dataclass

TASK_QUEUE = "activity-session-cache"


@dataclass(frozen=True)
class StepEvent:
    """Sent by an activity when a step starts and again when it finishes."""

    workflow_id: str
    step: int
    worker: str
    # Earlier conversation turns this worker had to fetch before running the step.
    fetched: int
    finished: bool
