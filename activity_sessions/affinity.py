"""Compare how much fetching each mode causes and how many workflows share a worker."""

import argparse
import asyncio
import contextlib
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from multiprocessing.queues import Queue
from typing import Literal, get_args

from rich.console import Console, Group, RenderableType
from rich.text import Text
from temporalio.client import Client

from activity_sessions import StepEvent
from activity_sessions.display import GRID_LEGEND, check_list, stat_tiles, turn_grid
from activity_sessions.fleet import (
    Fleet,
    Turns,
    add_common_args,
    connect,
    new_event_queue,
    start_conversations,
)
from activity_sessions.live import run_live
from activity_sessions.worker import WorkerSpec

# none: ordinary task-queue routing. affinity: activities join the workflow's
# session on shared session workers. single-session: the same, on workers that
# each serve exactly one workflow.
Mode = Literal["none", "affinity", "single-session"]
LABELS: dict[Mode, str] = {
    "none": "No session",
    "affinity": "Affinity",
    "single-session": "Single session",
}


@dataclass
class ModeRun:
    mode: Mode
    workflow_ids: list[str]
    turns: Turns = field(default_factory=Turns)


def checks(run: ModeRun) -> list[tuple[bool, str]]:
    """What the mode promises; ordinary routing promises nothing."""
    if run.mode == "none":
        return []
    label = LABELS[run.mode]
    one_worker = all(
        len({event.worker for event in run.turns.of(w)}) == 1 for w in run.workflow_ids
    )
    no_fetch = not any(event.fetched for event in run.turns.events.values())
    results = [
        (
            one_worker and no_fetch,
            f"{label}: each workflow ran every turn on one worker without fetching",
        )
    ]
    if run.mode == "single-session":
        results.append(
            (
                all(len(w) == 1 for w in run.turns.workflows_by_worker().values()),
                f"{label}: each worker served exactly one workflow",
            )
        )
    return results


def metrics(run: ModeRun, fetch_seconds: float) -> dict[str, str]:
    fetched = sum(event.fetched for event in run.turns.events.values())
    most = max(map(len, run.turns.workflows_by_worker().values()))
    return {
        "Turns fetched": str(fetched),
        "Time spent fetching (s)": f"{fetched * fetch_seconds:.1f}",
        "Most workflows on one worker": str(most),
    }


async def run_mode(
    client: Client,
    args: argparse.Namespace,
    mode: Mode,
    events: "Queue[StepEvent]",
    on_progress: Callable[[ModeRun], None],
) -> ModeRun:
    """Run one batch of workflows on a fresh worker fleet for this mode."""
    prefix = f"{mode}-{uuid.uuid4().hex[:6]}"
    single_session = mode == "single-session"
    # Single session: one worker per workflow, each bound to it for its lifetime.
    workers = [
        WorkerSpec(
            f"w{index}",
            stable_identity=f"{prefix}-w{index}" if single_session else None,
        )
        for index in range(1, (args.workflows if single_session else args.workers) + 1)
    ]
    run = ModeRun(mode, [f"{prefix}-{i:02}" for i in range(1, args.workflows + 1)])
    task_queue = f"activity-sessions-{prefix}"
    fleet = Fleet(task_queue, args, events)
    try:
        # Start workflows only once every worker polls, so none gets a head start.
        await fleet.start(*workers)
        handles = await start_conversations(
            client, run.workflow_ids, task_queue, mode != "none", args.steps
        )
        results = asyncio.gather(*(handle.result() for handle in handles))
        # Workflows can complete just before their last turn's event arrives.
        while not results.done() or len(run.turns.events) < args.workflows * args.steps:
            await asyncio.sleep(0.1)
            run.turns.drain(events)
            on_progress(run)
        await results
    finally:
        fleet.stop()
    return run


def grid(run: ModeRun, steps: int) -> Group:
    return Group(
        Text(LABELS[run.mode], style="bold"),
        turn_grid(run.workflow_ids, run.turns, steps),
    )


def report(runs: Sequence[ModeRun], steps: int, fetch_seconds: float) -> Group:
    return Group(
        stat_tiles({LABELS[run.mode]: metrics(run, fetch_seconds) for run in runs}),
        *(grid(run, steps) for run in runs),
        Text(GRID_LEGEND, style="bright_black"),
        check_list([check for run in runs for check in checks(run)]),
    )


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--modes",
        nargs="+",
        choices=get_args(Mode),
        default=["none", "affinity"],
        help="Modes to run and compare (default: none affinity)",
    )
    parser.add_argument("--workflows", type=int, default=8, help="Workflows per mode")
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Workers for none and affinity; single-session starts one per workflow",
    )
    add_common_args(parser, fetch_seconds=0.5, turn_seconds=0.1)
    args = parser.parse_args()

    client = await connect()
    events = new_event_queue()
    console = Console()
    current: list[ModeRun] = []

    async def work(refresh: Callable[[], None]) -> list[ModeRun]:
        def on_progress(run: ModeRun) -> None:
            current[:] = [run]
            refresh()

        return [
            await run_mode(client, args, mode, events, on_progress)
            for mode in args.modes
        ]

    runs = await run_live(
        console, args.no_live, lambda: grid(current[0], args.steps), work
    )
    console.print(report(runs, args.steps, args.fetch_seconds))
    if not all(ok for run in runs for ok, _ in checks(run)):
        raise SystemExit(1)


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
