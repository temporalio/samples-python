from dataclasses import dataclass

TASK_QUEUE = "activity-session-cache"


@dataclass
class StepResult:
    step: int
    worker_identity: str
    session_enabled: bool
    cache_hit: bool
