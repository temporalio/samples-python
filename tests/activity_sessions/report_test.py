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


def batch(affinity_enabled: bool, placements: dict[str, list[tuple[str, bool]]]):
    result = Batch(affinity_enabled, list(placements))
    for workflow_id, steps in placements.items():
        for step, (worker, cache_hit) in enumerate(steps, 1):
            result.record(StepEvent(workflow_id, step, worker, cache_hit, True))
        result.durations[workflow_id] = sum(not hit for _, hit in steps) * 1.0
    result.wall_seconds = max(result.durations.values())
    return result


def render(*batches: Batch) -> str:
    output = io.StringIO()
    Console(file=output, width=140, color_system=None).print(
        summary(batches, 3, 2, 1.0)
    )
    return output.getvalue()


def test_comparison_reports_loads_and_speedup() -> None:
    off = batch(
        False, {"off-1": [("worker-1", False), ("worker-2", False), ("worker-1", True)]}
    )
    on = batch(
        True, {"on-1": [("worker-2", False), ("worker-2", True), ("worker-2", True)]}
    )
    text = render(off, on)
    assert "Affinity OFF" in text and "Affinity ON" in text
    assert "●1" in text and "○2" in text
    assert "50% fewer" in text
    assert "2.0x faster" in text
    assert "Verified: each of 1 workflow(s)" in text


def test_affinity_violations_flag_split_or_repeated_loads() -> None:
    result = batch(
        True,
        {
            "good": [("worker-1", False), ("worker-1", True), ("worker-1", True)],
            "split": [("worker-1", False), ("worker-2", False), ("worker-1", True)],
        },
    )
    assert affinity_violations(result) == ["split"]
    assert "Affinity not observed for: split" in render(result)


def test_unknown_workflow_event_is_rejected() -> None:
    result = Batch(True, ["known"])
    with pytest.raises(ValueError):
        result.record(StepEvent("other", 1, "worker-1", False, True))


def test_worker_configuration_lists_roles() -> None:
    output = io.StringIO()
    print_worker_configuration(
        {"worker-1": True, "worker-2": False},
        Console(file=output, width=140, color_system=None),
    )
    assert "Workflow + activity" in output.getvalue()
    assert "Activity only" in output.getvalue()
