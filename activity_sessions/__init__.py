from dataclasses import dataclass

TASK_QUEUE = "activity-session-cache"


def worker_configuration(
    session_workers: int, activity_workers: int
) -> dict[str, bool]:
    if (
        session_workers < 0
        or activity_workers < 0
        or session_workers + activity_workers == 0
    ):
        raise ValueError("Worker counts must be nonnegative, with at least one worker")
    return {
        f"worker-{index + 1}": index < session_workers
        for index in range(session_workers + activity_workers)
    }


@dataclass
class StepResult:
    step: int
    worker_identity: str
    session_enabled: bool
    cache_hit: bool
