from collections.abc import Sequence
from dataclasses import dataclass

from rich import box
from rich.console import Console
from rich.table import Table

from activity_sessions import StepResult


@dataclass
class WorkflowResult:
    workflow_id: str
    steps: list[StepResult]
    workflow_workers: set[str]


def print_worker_configuration(workers: dict[str, bool], console: Console) -> None:
    table = Table(title="Worker configuration", box=box.ROUNDED)
    table.add_column("Worker", style="cyan")
    table.add_column("Role")
    table.add_column("Session support")
    for identity, session_enabled in workers.items():
        table.add_row(
            identity,
            "Workflow + activity" if session_enabled else "Activity only",
            "[green]ON[/green]" if session_enabled else "[dim]OFF[/dim]",
        )
    console.print(table)


def print_results(
    affinity_enabled: bool,
    runs: Sequence[WorkflowResult],
    known_workers: dict[str, bool],
    console: Console | None = None,
) -> None:
    console = console or Console()
    mode = "ON" if affinity_enabled else "OFF"
    console.rule(f"Activity affinity {mode} — {len(runs)} workflow(s)")
    table = Table(title="Workflow execution", box=box.SIMPLE)
    for column in (
        "Workflow",
        "Workflow worker",
        "Step",
        "Activity worker",
        "Session support",
        "Cache",
    ):
        table.add_column(column)
    for run in runs:
        for step in run.steps:
            table.add_row(
                run.workflow_id,
                ", ".join(sorted(run.workflow_workers)),
                str(step.step),
                step.worker_identity,
                "[green]ON[/green]" if step.session_enabled else "[dim]OFF[/dim]",
                "[green]HIT[/green]" if step.cache_hit else "[yellow]MISS[/yellow]",
                end_section=step.step == 3,
            )
    console.print(table)
    results = [step for run in runs for step in run.steps]
    roles = {
        **known_workers,
        **{step.worker_identity: step.session_enabled for step in results},
    }
    totals = Table(title="Per-worker totals for this batch", box=box.SIMPLE)
    for column in ("Worker", "Activities", "Hits", "Misses / context loads"):
        totals.add_column(column)
    for identity in roles:
        steps = [step for step in results if step.worker_identity == identity]
        hits = sum(step.cache_hit for step in steps)
        totals.add_row(identity, str(len(steps)), str(hits), str(len(steps) - hits))
    console.print(totals)
    if affinity_enabled:
        assert runs
        for run in runs:
            assert len(run.steps) == 3
            assert len(run.workflow_workers) == 1
            assert all(
                step.worker_identity in run.workflow_workers for step in run.steps
            )
            assert [step.cache_hit for step in run.steps] == [False, True, True]
        console.print(
            f"[green]Verified: {len(runs)} context load(s), then two cache hits "
            "per workflow on its owner.[/green]"
        )
    else:
        console.print(
            "[dim]Ordinary placement is not guaranteed; activities may also colocate by chance.[/dim]"
        )
