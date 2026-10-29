"""Show single-session workers binding workflows to stable identities, across the
loss of the whole fleet."""

import argparse
import asyncio
import contextlib
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field

from activity_sessions.fleet import (
    Fleet,
    Turns,
    add_common_args,
    connect,
    new_event_queue,
    start_conversations,
)
from activity_sessions.worker import WorkerSpec

PHASES = ["Bind", "Kill the fleet", "New identities", "Rebind"]


@dataclass
class Lifecycle:
    """What the run has done so far, for the checks and the display."""

    workflow_ids: list[str]
    steps: int
    phase: int = 0
    turns: Turns = field(default_factory=Turns)
    # Worker identity -> whether its process is running.
    alive: dict[str, bool] = field(default_factory=dict)
    checks: list[tuple[bool, str]] = field(default_factory=list)

    def progress(self) -> dict[str, int]:
        return {w: len(self.turns.of(w)) for w in self.workflow_ids}

    def worker_of(self, workflow_id: str) -> str | None:
        """The worker identity a workflow is bound to, once it has run a turn."""
        turns = self.turns.of(workflow_id)
        return turns[-1].worker if turns else None


async def run_lifecycle(
    args: argparse.Namespace, life: Lifecycle, refresh: Callable[[], None]
) -> None:
    prefix = life.workflow_ids[0].rsplit("-", 1)[0]
    task_queue = f"activity-sessions-{prefix}"
    events = new_event_queue()
    fleet = Fleet(task_queue, args, events)

    def workers(group: str, count: int) -> list[WorkerSpec]:
        return [
            WorkerSpec(f"{group}{i}", stable_identity=f"{prefix}-{group}{i}")
            for i in range(1, count + 1)
        ]

    originals = workers("a", args.workers)
    replacements = workers("b", args.workflows - args.workers)

    async def start(specs: list[WorkerSpec]) -> None:
        await fleet.start(*specs)
        life.alive.update({spec.identity: True for spec in specs})

    def kill(specs: list[WorkerSpec]) -> None:
        fleet.kill(*(spec.identity for spec in specs))
        life.alive.update({spec.identity: False for spec in specs})

    async def watch(until: Callable[[], bool]) -> None:
        """Record turns until the condition holds."""
        while True:
            life.turns.drain(events)
            refresh()
            if until():
                return
            await asyncio.sleep(0.1)

    async def watch_for(seconds: float) -> None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + seconds
        await watch(lambda: loop.time() >= deadline)

    def done(workflow_ids: list[str]) -> bool:
        return all(life.progress()[w] == args.steps for w in workflow_ids)

    try:
        # 1. Each original worker binds to one workflow; the rest get none.
        await start(originals)
        await start_conversations(
            await connect(), life.workflow_ids, task_queue, True, args.steps
        )
        await watch(
            lambda: sum(n >= 2 for n in life.progress().values()) >= args.workers
        )
        bound = [w for w, n in life.progress().items() if n]
        unbound = [w for w in life.workflow_ids if w not in bound]
        life.checks.append(
            (
                len(bound) == args.workers,
                f"{len(bound)} workflows bound to the {args.workers} workers; "
                f"{len(unbound)} got none",
            )
        )

        # 2. With the whole fleet gone, nothing runs.
        life.phase = 1
        kill(originals)
        # Let turns that finished just before the kill arrive.
        await watch_for(0.5)
        stalled = life.progress()
        await watch_for(2)
        life.checks.append((life.progress() == stalled, "Every workflow stalled"))

        # 3. Workers with new identities take only the unbound workflows.
        life.phase = 2
        await start(replacements)
        await watch(lambda: done(unbound))
        life.checks.append(
            (
                all(life.progress()[w] == stalled[w] for w in bound),
                "New identities ran the unbound workflows; the bound ones stayed stalled",
            )
        )

        # 4. Restarted with their stable identities, the original workers resume
        # their own workflows.
        life.phase = 3
        await start(originals)
        await watch(lambda: done(life.workflow_ids))
        life.checks.append(
            (
                all(len(w) == 1 for w in life.turns.workflows_by_worker().values())
                and all(
                    len({e.worker for e in life.turns.of(w)}) == 1
                    for w in life.workflow_ids
                ),
                "Each workflow ran every turn on its own worker identity",
            )
        )
    finally:
        fleet.stop()


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflows", type=int, default=6, help="Workflows (N)")
    parser.add_argument(
        "--workers", type=int, default=3, help="Original workers (M, fewer than N)"
    )
    add_common_args(parser, fetch_seconds=0.2, turn_seconds=0.3)
    args = parser.parse_args()
    if not 0 < args.workers < args.workflows:
        parser.error("--workers must be at least 1 and fewer than --workflows")

    prefix = f"single-session-{uuid.uuid4().hex[:6]}"
    life = Lifecycle(
        [f"{prefix}-{i:02}" for i in range(1, args.workflows + 1)], args.steps
    )
    shown: list[int] = []

    def refresh() -> None:
        if life.phase not in shown:
            shown.append(life.phase)
            print(f"Phase {life.phase + 1}/{len(PHASES)}: {PHASES[life.phase]}")

    await run_lifecycle(args, life, refresh)
    for ok, message in life.checks:
        print(f"{'ok' if ok else 'FAIL'} - {message}")
    if not all(ok for ok, _ in life.checks):
        raise SystemExit(1)


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
