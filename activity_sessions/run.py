import argparse
import asyncio
import contextlib
import multiprocessing
import queue
import time
import uuid
from datetime import timedelta
from multiprocessing.queues import Queue
from typing import TYPE_CHECKING

from rich.console import Console
from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from activity_sessions import TASK_QUEUE, StepEvent
from activity_sessions.display import (
    Batch,
    affinity_violations,
    print_worker_configuration,
    summary,
)
from activity_sessions.worker import worker_process
from activity_sessions.workflows import ConversationInput, ProcessConversation

if TYPE_CHECKING:
    from activity_sessions.live import LiveView


async def run_batch(
    client: Client,
    args: argparse.Namespace,
    affinity_enabled: bool,
    events: "Queue[StepEvent]",
    view: "LiveView | None",
) -> Batch:
    prefix = f"{'on' if affinity_enabled else 'off'}-{uuid.uuid4().hex[:6]}"
    batch = Batch(
        affinity_enabled,
        [f"{prefix}-{index:02}" for index in range(1, args.workflows + 1)],
    )
    started = time.monotonic()

    async def run_workflow(workflow_id: str) -> None:
        begin = time.monotonic()
        await client.execute_workflow(
            ProcessConversation.run,
            ConversationInput(affinity_enabled, args.steps),
            id=workflow_id,
            task_queue=args.task_queue,
            execution_timeout=timedelta(minutes=5),
        )
        batch.durations[workflow_id] = time.monotonic() - begin

    pending = {asyncio.create_task(run_workflow(w)) for w in batch.workflow_ids}
    expected_steps = args.workflows * args.steps
    # Workflows can complete just before their activities' last events arrive.
    while pending or len(batch.finished_steps()) < expected_steps:
        if pending:
            done, pending = await asyncio.wait(pending, timeout=0.1)
            for task in done:
                task.result()
        else:
            await asyncio.sleep(0.05)
        while True:
            try:
                batch.record(events.get_nowait())
            except queue.Empty:
                break
        if view:
            view.show(batch)
    batch.wall_seconds = time.monotonic() - started
    return batch


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a worker pool and compare activity affinity and cache reuse."
    )
    parser.add_argument(
        "--affinity", choices=["compare", "on", "off"], default="compare"
    )
    parser.add_argument("--task-queue", default=f"{TASK_QUEUE}-{uuid.uuid4().hex[:8]}")
    parser.add_argument("--session-workers", type=int, default=4)
    parser.add_argument(
        "--activity-workers",
        type=int,
        default=0,
        help="Additional activity-only workers without session support",
    )
    parser.add_argument(
        "--workflows", type=int, default=20, help="Concurrent workflows per mode"
    )
    parser.add_argument(
        "--steps", type=int, default=5, help="Sequential activities per workflow"
    )
    parser.add_argument(
        "--load-seconds",
        type=float,
        default=1.0,
        help="Simulated latency of loading context on a cache miss",
    )
    parser.add_argument(
        "--no-live", action="store_true", help="Only print the final summary"
    )
    args = parser.parse_args()
    if args.session_workers < 1:
        parser.error("The demo needs at least one session worker to run workflows")
    if args.activity_workers < 0:
        parser.error("--activity-workers cannot be negative")
    if args.workflows < 1 or args.steps < 1:
        parser.error("--workflows and --steps must be at least 1")

    workers = {
        f"worker-{index}": index <= args.session_workers
        for index in range(1, args.session_workers + args.activity_workers + 1)
    }
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)
    console = Console()
    print_worker_configuration(workers, console)

    # Spawn gives each worker a fresh interpreter, SDK runtime, and private cache.
    context = multiprocessing.get_context("spawn")
    events: "Queue[StepEvent]" = context.Queue()
    ready = context.Barrier(len(workers) + 1)
    processes = [
        context.Process(
            target=worker_process,
            args=(
                identity,
                session_enabled,
                args.task_queue,
                args.load_seconds,
                events,
                ready,
            ),
            daemon=True,
        )
        for identity, session_enabled in workers.items()
    ]
    modes = [False, True] if args.affinity == "compare" else [args.affinity == "on"]
    batches = []
    try:
        for process in processes:
            process.start()
        with console.status("Starting workers..."):
            # Start workflows only once every worker polls, so none gets a head start.
            await asyncio.to_thread(ready.wait, 60)
        view = None
        if not args.no_live and console.is_terminal:
            from activity_sessions.live import LiveView

            view = LiveView(workers, args.steps, console)
        with view or contextlib.nullcontext():
            for affinity_enabled in modes:
                batches.append(
                    await run_batch(client, args, affinity_enabled, events, view)
                )
    finally:
        ready.abort()
        for process in processes:
            process.terminate()
        for process in processes:
            process.join()

    console.print(summary(batches, args.steps, len(workers), args.load_seconds))
    if any(affinity_violations(batch) for batch in batches if batch.affinity_enabled):
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
