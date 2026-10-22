import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from rich import box
from rich.console import Console, Group, RenderableType
from rich.table import Table
from rich.text import Text

from activity_sessions import StepEvent

WORKER_COLORS = [
    "cyan",
    "magenta",
    "green",
    "yellow",
    "blue",
    "red",
    "bright_cyan",
    "bright_magenta",
    "bright_green",
    "bright_yellow",
]
LEGEND = (
    "○2 worker 2 had every earlier turn   ●2(3) worker 2 fetched 3 missing turns   "
    "◌ fetching"
)


@dataclass
class Batch:
    affinity_enabled: bool
    workflow_ids: list[str]
    steps: dict[str, dict[int, StepEvent]] = field(default_factory=dict)
    durations: dict[str, float] = field(default_factory=dict)
    wall_seconds: float = 0.0

    @property
    def mode(self) -> str:
        return f"Affinity {'ON' if self.affinity_enabled else 'OFF'}"

    def record(self, event: StepEvent) -> None:
        if event.workflow_id not in self.workflow_ids:
            raise ValueError(f"Event for unknown workflow {event.workflow_id}")
        self.steps.setdefault(event.workflow_id, {})[event.step] = event

    def cached_turns(self, workflow_id: str) -> dict[str, int]:
        """Turns each worker holds for a workflow: everything up to its latest step."""
        held: dict[str, int] = {}
        for event in self.steps.get(workflow_id, {}).values():
            if event.finished:
                held[event.worker] = max(held.get(event.worker, 0), event.step + 1)
        return held

    def finished_steps(self) -> list[StepEvent]:
        return [
            event
            for steps in self.steps.values()
            for event in steps.values()
            if event.finished
        ]


def worker_number(worker: str) -> int:
    return int(worker.rsplit("-", 1)[1])


def worker_color(worker: str) -> str:
    return WORKER_COLORS[(worker_number(worker) - 1) % len(WORKER_COLORS)]


def placement_strip(
    batch: Batch, steps: int, worker_count: int, show_pending: bool = False
) -> Table:
    """One row per workflow and one cell per step: glyph = fetches, color = worker."""
    width = len(f"●{worker_count}({steps - 1})")
    table = Table(box=None, show_header=False, padding=(0, 1, 0, 0))
    table.add_column(style="dim")
    table.add_column()
    table.add_column(justify="right")
    table.add_column(justify="right", style="dim")
    for index, workflow_id in enumerate(batch.workflow_ids, 1):
        events = batch.steps.get(workflow_id, {})
        if not events and not show_pending:
            continue
        cells = Text()
        for step in range(steps):
            event = events.get(step)
            if event is None:
                cells.append("·".ljust(width) + " ", style="dim")
                continue
            number = worker_number(event.worker)
            if not event.fetched:
                cell = f"○{number}"
            else:
                cell = f"{'●' if event.finished else '◌'}{number}({event.fetched})"
            cells.append(cell.ljust(width) + " ", style=worker_color(event.worker))
        fetched = sum(event.fetched for event in events.values())
        duration = batch.durations.get(workflow_id)
        table.add_row(
            f"wf-{index:02}",
            cells,
            f"{duration:.1f}s" if duration is not None else "",
            f"{fetched} fetched" if events else "",
        )
    return table


def print_worker_configuration(workers: Mapping[str, bool], console: Console) -> None:
    table = Table(title="Worker configuration", box=box.ROUNDED)
    table.add_column("Worker")
    table.add_column("Role")
    table.add_column("Session support")
    for identity, session_enabled in workers.items():
        table.add_row(
            Text(identity, style=worker_color(identity)),
            "Workflow + activity" if session_enabled else "Activity only",
            "[green]ON[/green]" if session_enabled else "[dim]OFF[/dim]",
        )
    console.print(table)


def percentile(values: Sequence[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)]


def affinity_violations(batch: Batch) -> list[str]:
    """Workflows whose turns did not all run on one worker without fetching."""
    return [
        workflow_id
        for workflow_id in batch.workflow_ids
        if len(batch.cached_turns(workflow_id)) != 1
        or any(event.fetched for event in batch.steps[workflow_id].values())
    ]


def comparison_table(batches: Sequence[Batch], fetch_seconds: float) -> Table:
    table = Table(title="Impact", box=box.SIMPLE_HEAD)
    table.add_column("")
    for batch in batches:
        table.add_column(batch.mode, justify="right")
    compare = len(batches) == 2
    if compare:
        table.add_column("Change", justify="right", style="bold green")

    def add(
        label: str, values: list[float], fmt: str, change: str | None = None
    ) -> None:
        row = [label, *(format(value, fmt) for value in values)]
        if compare:
            row.append(change or "")
        table.add_row(*row)

    fetched = [
        float(sum(event.fetched for event in batch.finished_steps()))
        for batch in batches
    ]
    fetching_steps = [
        float(sum(bool(event.fetched) for event in batch.finished_steps()))
        for batch in batches
    ]
    fleet_turns = [
        sum(
            sum(batch.cached_turns(workflow_id).values())
            for workflow_id in batch.workflow_ids
        )
        / len(batch.workflow_ids)
        for batch in batches
    ]
    p50 = [percentile(list(batch.durations.values()), 0.5) for batch in batches]
    p95 = [percentile(list(batch.durations.values()), 0.95) for batch in batches]
    walls = [batch.wall_seconds for batch in batches]

    def fewer(values: list[float]) -> str | None:
        if not compare or not values[0]:
            return None
        return f"{1 - values[1] / values[0]:.0%} fewer"

    def faster(values: list[float]) -> str | None:
        if not compare or not values[1]:
            return None
        return f"{values[0] / values[1]:.1f}x faster"

    add("Turns fetched", fetched, ".0f", fewer(fetched))
    add("Steps that had to fetch", fetching_steps, ".0f", fewer(fetching_steps))
    add(
        "Time spent fetching (s)",
        [count * fetch_seconds for count in fetched],
        ".1f",
        fewer(fetched),
    )
    add("Cached turns across fleet per workflow", fleet_turns, ".1f")
    add("Workflow latency p50 (s)", p50, ".1f", faster(p50))
    add("Workflow latency p95 (s)", p95, ".1f", faster(p95))
    add("Batch wall time (s)", walls, ".1f", faster(walls))
    return table


def summary(
    batches: Sequence[Batch], steps: int, worker_count: int, fetch_seconds: float
) -> RenderableType:
    strips = Table.grid(padding=(0, 4))
    for batch in batches:
        strips.add_column()
    strips.add_row(*(Text(batch.mode, style="bold") for batch in batches))
    strips.add_row(*(placement_strip(batch, steps, worker_count) for batch in batches))
    parts: list[RenderableType] = [
        strips,
        Text(LEGEND, style="dim"),
        comparison_table(batches, fetch_seconds),
    ]
    for batch in batches:
        if not batch.affinity_enabled:
            continue
        violations = affinity_violations(batch)
        if violations:
            parts.append(
                Text(
                    f"Affinity not observed for: {', '.join(violations)}",
                    style="bold red",
                )
            )
        else:
            parts.append(
                Text(
                    f"Verified: each of {len(batch.workflow_ids)} workflow(s) ran "
                    "every turn on one worker without fetching earlier turns.",
                    style="green",
                )
            )
    return Group(*parts)
