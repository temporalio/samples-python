"""Optional live terminal view; the demo runs the same without it (--no-live)."""

from collections.abc import Mapping
from types import TracebackType

from rich.columns import Columns
from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

from activity_sessions.display import (
    LEGEND,
    Batch,
    placement_strip,
    worker_color,
)


class LiveView:
    def __init__(self, workers: Mapping[str, bool], steps: int, console: Console):
        self.workers = workers
        self.steps = steps
        self.live = Live(console=console, auto_refresh=False, transient=True)

    def __enter__(self) -> "LiveView":
        self.live.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.live.stop()

    def show(self, batch: Batch) -> None:
        self.live.update(self.render(batch), refresh=True)

    def render(self, batch: Batch) -> RenderableType:
        labels = {workflow_id: i for i, workflow_id in enumerate(batch.workflow_ids, 1)}
        events = [event for steps in batch.steps.values() for event in steps.values()]
        panels = []
        for worker, session_enabled in self.workers.items():
            mine = [event for event in events if event.worker == worker]
            cached = sorted(
                labels[event.workflow_id]
                for event in mine
                if not event.cache_hit and event.finished
            )
            loading = sum(not event.cache_hit and not event.finished for event in mine)
            hits = sum(event.cache_hit for event in mine)
            body = Text()
            body.append(f"loads {len(cached) + loading}  hits {hits}\n")
            body.append("◌ " * loading + "\n", style="yellow")
            body.append("cache: ", style="dim")
            body.append(" ".join(f"{label:02}" for label in cached))
            title = worker if session_enabled else f"{worker} (activity only)"
            panels.append(
                Panel(
                    body,
                    title=Text(title, style=f"bold {worker_color(worker)}"),
                    width=29,
                )
            )
        entries = sum(not event.cache_hit for event in events)
        started = len(batch.steps)
        fleet = Text(
            f"Fleet: {entries} cache entries for {started} started workflow(s)"
            + (f" ({entries / started:.1f} copies each)" if started else ""),
            style="bold",
        )
        return Group(
            Rule(
                Text(
                    f"{batch.mode} - {len(batch.workflow_ids)} workflow(s)",
                    style="bold",
                )
            ),
            Columns(panels),
            fleet,
            placement_strip(batch, self.steps, len(self.workers), show_pending=True),
            Text(LEGEND, style="dim"),
        )
