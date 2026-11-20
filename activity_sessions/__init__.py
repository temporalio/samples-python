from dataclasses import dataclass


@dataclass(frozen=True)
class StepEvent:
    """Sent by an activity when it finishes a conversation turn."""

    workflow_id: str
    step: int
    worker: str
    # Earlier turns this worker had to fetch before running the step.
    fetched: int
