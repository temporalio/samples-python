"""Rich building blocks shared by the sample's entrypoints."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from rich import box
from rich.columns import Columns
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from activity_sessions.fleet import Turns

# Turns fetched is a magnitude: one hue, from muted (none) to strong (many).
FETCH_SHADES = [
    "bright_black",
    "color(223)",
    "color(215)",
    "color(208)",
    "bold color(202)",
]
GRID_LEGEND = (
    "w2: worker w2 ran the turn   w2+3: it first fetched 3 missing turns (shaded)"
)

WorkflowState = Literal["waiting", "running", "stalled", "done"]
# Status colors always come with an icon and a label.
WORKFLOW_STATES: dict[WorkflowState, tuple[str, str]] = {
    "waiting": ("… waiting", "bright_black"),
    "running": ("▶ running", "green"),
    "stalled": ("⏸ stalled", "yellow"),
    "done": ("✓ done", "bright_black"),
}


def turn_grid(workflow_ids: Sequence[str], turns: Turns, steps: int) -> Table:
    """One row per workflow, one cell per turn: who ran it, and what it fetched."""
    table = Table(box=None, show_header=False, padding=(0, 1, 0, 0))
    for index, workflow_id in enumerate(workflow_ids, 1):
        cells = Text()
        for step in range(steps):
            event = turns.events.get((workflow_id, step))
            if event is None:
                cells.append(f"{'·':<6}", style="bright_black")
                continue
            label = event.worker + (f"+{event.fetched}" if event.fetched else "")
            shade = FETCH_SHADES[min(event.fetched, len(FETCH_SHADES) - 1)]
            cells.append(f"{label:<6}", style=shade)
        table.add_row(Text(f"wf-{index:02}", style="bright_black"), cells)
    return table


def stat_tiles(columns: Mapping[str, Mapping[str, str]]) -> Columns:
    """A headline tile per column: each metric's value above its label."""
    tiles = []
    for title, metrics in columns.items():
        body = Text()
        for label, value in metrics.items():
            body.append(f"{value}\n", style="bold")
            body.append(f"{label}\n", style="bright_black")
        body.rstrip()
        tiles.append(Panel(body, title=title, width=32, box=box.ROUNDED))
    return Columns(tiles)


def check_list(checks: Sequence[tuple[bool, str]]) -> Group:
    return Group(
        *(
            Text(f"{'✓' if ok else '✗'} {message}", style="green" if ok else "bold red")
            for ok, message in checks
        )
    )


def phase_banner(phase: int, phases: Sequence[str]) -> Rule:
    return Rule(Text(f"Phase {phase + 1}/{len(phases)}: {phases[phase]}", style="bold"))


@dataclass(frozen=True)
class WorkflowRow:
    workflow_id: str
    state: WorkflowState
    worker: str | None
    turns: int
    steps: int


def workflow_table(rows: Sequence[WorkflowRow]) -> Table:
    table = Table(title="Workflows", box=box.SIMPLE_HEAD, title_justify="left")
    for column in ["Workflow", "State", "Bound to", "Turns"]:
        table.add_column(column)
    for index, row in enumerate(rows, 1):
        label, style = WORKFLOW_STATES[row.state]
        table.add_row(
            f"wf-{index:02}",
            Text(label, style=style),
            row.worker or Text("unbound", style="bright_black"),
            ProgressBar(total=row.steps, completed=row.turns, width=row.steps * 2),
        )
    return table


@dataclass(frozen=True)
class WorkerRow:
    identity: str
    alive: bool
    serving: str | None


def worker_table(rows: Sequence[WorkerRow]) -> Table:
    table = Table(title="Workers", box=box.SIMPLE_HEAD, title_justify="left")
    for column in ["Worker", "Process", "Serving"]:
        table.add_column(column)
    for row in rows:
        table.add_row(
            row.identity,
            Text("● alive", style="green")
            if row.alive
            else Text("✖ killed", style="red"),
            row.serving or Text("—", style="bright_black"),
        )
    return table
