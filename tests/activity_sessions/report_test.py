from activity_sessions import StepResult
from activity_sessions.starter import print_results


def test_report_includes_idle_worker_and_session_setting(capsys) -> None:
    print_results(
        True,
        [
            StepResult(1, "worker-1", True, False),
            StepResult(2, "worker-1", True, True),
            StepResult(3, "worker-1", True, True),
        ],
        {"worker-1"},
        {"worker-1": True, "worker-2": False},
    )
    lines = capsys.readouterr().out.splitlines()
    assert any(line.split() == ["1", "worker-1", "ON", "MISS"] for line in lines)
    assert any(line.split() == ["worker-1", "ON", "3", "2", "1"] for line in lines)
    assert any(line.split() == ["worker-2", "OFF", "0", "0", "0"] for line in lines)
    assert any("Verified:" in line for line in lines)


def test_ordinary_routing_may_colocate_by_chance(capsys) -> None:
    print_results(
        False,
        [StepResult(step, "worker-1", True, step != 1) for step in (1, 2, 3)],
        {"worker-1"},
        {"worker-1": True},
    )
    assert "may also colocate by chance" in capsys.readouterr().out
