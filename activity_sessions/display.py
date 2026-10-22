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
LEGEND = "● context load (miss)   ○ cache hit   ◌ loading   number/color = worker"


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
    """One row per workflow and one cell per step: glyph = cache result, color = worker."""
    width = len(str(worker_count)) + 1
    table = Table(box=None, show_header=False, padding=(0, 1, 0, 0))
    table.add_column(style="dim")
    table.add_column()
    table.add_column(justify="right")
    for index, workflow_id in enumerate(batch.workflow_ids, 1):
        events = batch.steps.get(workflow_id, {})
        if not events and not show_pending:
            continue
        cells = Text()
        for step in range(1, steps + 1):
            event = events.get(step)
            if event is None:
                cells.append("·".ljust(width) + " ", style="dim")
                continue
            if event.cache_hit:
                glyph = "○"
            else:
                glyph = "●" if event.finished else "◌"
            cell = f"{glyph}{worker_number(event.worker)}".ljust(width) + " "
            cells.append(cell, style=worker_color(event.worker))
        duration = batch.durations.get(workflow_id)
        table.add_row(
            f"wf-{index:02}", cells, f"{duration:.1f}s" if duration is not None else ""
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
    """Workflows that did not load once and then reuse the cache on a single worker."""
    violations = []
    for workflow_id in batch.workflow_ids:
        events = sorted(batch.steps.get(workflow_id, {}).values(), key=lambda e: e.step)
        workers = {event.worker for event in events}
        hits = [event.cache_hit for event in events]
        if len(workers) != 1 or hits != [False] + [True] * (len(hits) - 1):
            violations.append(workflow_id)
    return violations


def comparison_table(batches: Sequence[Batch], load_seconds: float) -> Table:
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

    loads = [
        float(sum(not event.cache_hit for event in batch.finished_steps()))
        for batch in batches
    ]
    copies = [load / len(batch.workflow_ids) for load, batch in zip(loads, batches)]
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

    add("Context loads", loads, ".0f", fewer(loads))
    add("Cache copies per workflow", copies, ".1f")
    add("Time spent loading (s)", [load * load_seconds for load in loads], ".1f")
    add("Workflow latency p50 (s)", p50, ".1f", faster(p50))
    add("Workflow latency p95 (s)", p95, ".1f", faster(p95))
    add("Batch wall time (s)", walls, ".1f", faster(walls))
    return table


def summary(
    batches: Sequence[Batch], steps: int, worker_count: int, load_seconds: float
) -> RenderableType:
    strips = Table.grid(padding=(0, 4))
    for batch in batches:
        strips.add_column()
    strips.add_row(*(Text(batch.mode, style="bold") for batch in batches))
    strips.add_row(*(placement_strip(batch, steps, worker_count) for batch in batches))
    parts: list[RenderableType] = [
        strips,
        Text(LEGEND, style="dim"),
        comparison_table(batches, load_seconds),
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
                    f"Verified: each of {len(batch.workflow_ids)} workflow(s) loaded "
                    "its context once and reused it on a single worker.",
                    style="green",
                )
            )
    return Group(*parts)
