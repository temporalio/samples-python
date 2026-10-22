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
        held = {
            workflow_id: batch.cached_turns(workflow_id)
            for workflow_id in batch.workflow_ids
        }
        events = [event for steps in batch.steps.values() for event in steps.values()]
        panels = []
        for worker, session_enabled in self.workers.items():
            mine = [event for event in events if event.worker == worker]
            fetched = sum(event.fetched for event in mine if event.finished)
            fetching = [event for event in mine if event.fetched and not event.finished]
            body = Text()
            body.append(f"steps {len(mine)}  turns fetched {fetched}\n")
            body.append(
                " ".join(f"◌({event.fetched})" for event in fetching) + "\n",
                style="yellow",
            )
            # wf:t means this worker holds the workflow's conversation through turn t.
            body.append("cache: ", style="dim")
            body.append(
                " ".join(
                    f"{index:02}:t{turns[worker] - 1}"
                    for index, turns in enumerate(held.values(), 1)
                    if worker in turns
                )
            )
            title = worker if session_enabled else f"{worker} (activity only)"
            panels.append(
                Panel(
                    body,
                    title=Text(title, style=f"bold {worker_color(worker)}"),
                    width=29,
                )
            )
        entries = sum(sum(turns.values()) for turns in held.values())
        started = len(batch.steps)
        fleet = Text(
            f"Fleet: {entries} cached turns for {started} started workflow(s)"
            + (f" ({entries / started:.1f} per workflow)" if started else ""),
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
