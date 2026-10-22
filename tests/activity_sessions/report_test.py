import io

import pytest
from rich.console import Console

from activity_sessions import StepEvent
from activity_sessions.display import (
    Batch,
    affinity_violations,
    print_worker_configuration,
    summary,
)


def batch(affinity_enabled: bool, placements: dict[str, list[tuple[str, int]]]):
    result = Batch(affinity_enabled, list(placements))
    for workflow_id, steps in placements.items():
        for step, (worker, fetched) in enumerate(steps):
            result.record(StepEvent(workflow_id, step, worker, fetched, True))
        result.durations[workflow_id] = 1.0 + sum(fetched for _, fetched in steps)
    result.wall_seconds = max(result.durations.values())
    return result


def render(*batches: Batch) -> str:
    output = io.StringIO()
    Console(file=output, width=160, color_system=None).print(
        summary(batches, 3, 2, 1.0)
    )
    return output.getvalue()


def test_comparison_reports_fetches_and_speedup() -> None:
    off = batch(False, {"off-1": [("worker-1", 0), ("worker-2", 1), ("worker-1", 1)]})
    on = batch(True, {"on-1": [("worker-2", 0), ("worker-2", 0), ("worker-2", 0)]})
    text = render(off, on)
    assert "Affinity OFF" in text and "Affinity ON" in text
    assert "●2(1)" in text and "○2" in text
    assert "2 fetched" in text
    assert "100% fewer" in text
    assert "3.0x faster" in text
    # OFF: worker-1 holds turns 0-2, worker-2 holds turns 0-1.
    assert "5.0" in text
    assert "Verified: each of 1 workflow(s)" in text


def test_cached_turns_track_each_workers_prefix() -> None:
    result = batch(False, {"wf": [("worker-1", 0), ("worker-2", 1), ("worker-1", 1)]})
    assert result.cached_turns("wf") == {"worker-1": 3, "worker-2": 2}


def test_affinity_violations_flag_split_or_fetching_workflows() -> None:
    result = batch(
        True,
        {
            "good": [("worker-1", 0), ("worker-1", 0), ("worker-1", 0)],
            "split": [("worker-1", 0), ("worker-2", 1), ("worker-1", 1)],
            "fetched": [("worker-1", 0), ("worker-1", 0), ("worker-1", 2)],
        },
    )
    assert affinity_violations(result) == ["split", "fetched"]
    assert "Affinity not observed for: split, fetched" in render(result)


def test_unknown_workflow_event_is_rejected() -> None:
    result = Batch(True, ["known"])
    with pytest.raises(ValueError):
        result.record(StepEvent("other", 0, "worker-1", 0, True))


def test_worker_configuration_lists_roles() -> None:
    output = io.StringIO()
    print_worker_configuration(
        {"worker-1": True, "worker-2": False},
        Console(file=output, width=140, color_system=None),
    )
    assert "Workflow + activity" in output.getvalue()
    assert "Activity only" in output.getvalue()
