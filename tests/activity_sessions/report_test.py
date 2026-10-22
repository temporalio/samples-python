import io

import pytest
from rich.console import Console

from activity_sessions import StepResult, worker_configuration
from activity_sessions.display import (
    WorkflowResult,
    print_results,
    print_worker_configuration,
)


def test_rich_report_separates_configuration_and_execution() -> None:
    output = io.StringIO()
    console = Console(file=output, width=140, color_system=None)
    workers = worker_configuration(1, 1)
    print_worker_configuration(workers, console)
    print_results(
        True,
        [
            WorkflowResult(
                "workflow-1",
                [StepResult(step, "worker-1", True, step != 1) for step in (1, 2, 3)],
                {"worker-1"},
            )
        ],
        workers,
        console,
    )
    text = output.getvalue()
    assert "Worker configuration" in text
    assert "Activity only" in text
    assert "OFF" in text
    assert "Workflow execution" in text
    assert "workflow-1" in text
    assert "Per-worker totals" in text
    assert "MISS" in text and "HIT" in text
    assert "Verified: 1 context load(s)" in text


def test_batch_reports_each_workflows_owner_and_its_cold_cache() -> None:
    output = io.StringIO()
    runs = [
        WorkflowResult(
            f"workflow-{index}",
            [
                StepResult(step, f"worker-{index}", True, step != 1)
                for step in (1, 2, 3)
            ],
            {f"worker-{index}"},
        )
        for index in (1, 2)
    ]
    print_results(
        True, runs, worker_configuration(2, 0), Console(file=output, width=140)
    )
    assert "Verified: 2 context load(s)" in output.getvalue()


def test_ordinary_routing_may_colocate_by_chance() -> None:
    output = io.StringIO()
    print_results(
        False,
        [
            WorkflowResult(
                "workflow-1", [StepResult(1, "worker-1", True, False)], {"worker-1"}
            )
        ],
        worker_configuration(1, 0),
        Console(file=output, width=140),
    )
    assert "may also colocate by chance" in output.getvalue()


def test_worker_counts_define_the_two_requested_pool_shapes() -> None:
    assert list(worker_configuration(10, 0).values()) == [True] * 10
    assert list(worker_configuration(1, 9).values()) == [True] + [False] * 9
    with pytest.raises(ValueError):
        worker_configuration(0, 0)
    with pytest.raises(ValueError):
        worker_configuration(-1, 2)
