from activity_sessions import StepEvent
from activity_sessions.affinity import Mode, ModeRun, checks, metrics


def run(mode: Mode, placements: dict[str, list[tuple[str, int]]]) -> ModeRun:
    """Workflow ID -> (worker, turns fetched) per step."""
    result = ModeRun(mode, list(placements))
    for workflow_id, steps in placements.items():
        for step, (worker, fetched) in enumerate(steps):
            result.turns.events[workflow_id, step] = StepEvent(
                workflow_id, step, worker, fetched
            )
    return result


def passed(result: ModeRun) -> list[bool]:
    return [ok for ok, _ in checks(result)]


def test_no_session_has_no_checks() -> None:
    assert checks(run("none", {"wf": [("w1", 0), ("w2", 1)]})) == []


def test_affinity_requires_one_worker_without_fetches() -> None:
    assert passed(run("affinity", {"wf": [("w1", 0), ("w1", 0)]})) == [True]
    assert passed(run("affinity", {"wf": [("w1", 0), ("w2", 1)]})) == [False]


def test_single_session_requires_one_workflow_per_worker() -> None:
    shared = run("single-session", {"a": [("w1", 0)], "b": [("w1", 0)]})
    assert passed(shared) == [True, False]
    dedicated = run("single-session", {"a": [("w1", 0)], "b": [("w2", 0)]})
    assert passed(dedicated) == [True, True]


def test_metrics() -> None:
    result = run("none", {"a": [("w1", 0), ("w1", 1)], "b": [("w1", 2)]})
    assert metrics(result, fetch_seconds=0.5) == {
        "Turns fetched": "3",
        "Time spent fetching (s)": "1.5",
        "Most workflows on one worker": "2",
    }
