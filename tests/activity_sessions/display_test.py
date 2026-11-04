import io

from rich.console import Console, RenderableType

from activity_sessions import StepEvent
from activity_sessions.display import (
    WorkerRow,
    WorkflowRow,
    check_list,
    stat_tiles,
    turn_grid,
    worker_table,
    workflow_table,
)
from activity_sessions.fleet import Turns


def render(renderable: RenderableType) -> str:
    output = io.StringIO()
    Console(file=output, width=120, color_system=None).print(renderable)
    return output.getvalue()


def test_turn_grid_labels_worker_and_fetches() -> None:
    turns = Turns()
    turns.events["wf", 0] = StepEvent("wf", 0, "w1", 0)
    turns.events["wf", 1] = StepEvent("wf", 1, "w2", 1)
    text = render(turn_grid(["wf"], turns, 3))
    assert "wf-01 w1    w2+1  ·" in text


def test_status_tables_and_checks_use_labels() -> None:
    text = render(
        workflow_table(
            [
                WorkflowRow("a", "stalled", "a1", 2, 4),
                WorkflowRow("b", "waiting", None, 0, 4),
            ]
        )
    )
    assert "⏸ stalled" in text and "… waiting" in text and "unbound" in text
    assert "✖ killed" in render(worker_table([WorkerRow("a1", False, "wf-01")]))
    assert "✗ bad" in render(check_list([(True, "good"), (False, "bad")]))


def test_stat_tiles_show_each_metric() -> None:
    text = render(stat_tiles({"Affinity": {"Turns fetched": "0"}}))
    assert "Affinity" in text and "Turns fetched" in text
