from temporalio.api.history.v1 import HistoryEvent, WorkflowTaskStartedEventAttributes
from temporalio.client import WorkflowHistory

from activity_sessions.models import StepResult, WorkerRegistration
from activity_sessions.starter import print_comparison, summarize_workers


def test_per_worker_report_includes_session_capability_and_idle_workers(capsys) -> None:
    roster = [
        WorkerRegistration("worker-1", True, 101, "queue"),
        WorkerRegistration("worker-2", False, 102, "queue"),
    ]
    results = [
        StepResult(1, "worker-1", True, False, 1, 1, "first-output"),
        StepResult(2, "worker-1", True, True, 0, 1, "second-output"),
    ]
    summaries = summarize_workers(results, roster)
    assert (summaries[0].steps, summaries[0].hits, summaries[0].misses) == (2, 1, 1)
    assert (summaries[0].artifact_reads, summaries[0].artifact_writes) == (1, 2)
    assert summaries[1].identity == "worker-2"
    assert not summaries[1].session_enabled
    assert summaries[1].steps == 0
    history = WorkflowHistory(
        "workflow",
        [
            HistoryEvent(
                workflow_task_started_event_attributes=WorkflowTaskStartedEventAttributes(
                    identity="worker-1"
                )
            )
        ],
    )
    print_comparison(True, "run-1", results, history, roster)
    output = capsys.readouterr().out
    assert "Session support" in output
    assert "worker-2" in output
    assert "OFF" in output
    assert "Verified:" in output


def test_disabled_comparison_does_not_require_scattered_placement(capsys) -> None:
    results = [StepResult(1, "worker-1", True, False, 1, 1, "output")]
    history = WorkflowHistory("workflow", [])
    print_comparison(False, "run-1", results, history, [])
    assert "placement is not guaranteed" in capsys.readouterr().out
