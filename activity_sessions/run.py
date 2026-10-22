import argparse
import asyncio
import multiprocessing
import uuid
from datetime import timedelta
from pathlib import Path

from rich.console import Console
from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from activity_sessions import TASK_QUEUE, worker_configuration
from activity_sessions.display import (
    WorkflowResult,
    print_results,
    print_worker_configuration,
)
from activity_sessions.worker import worker_process
from activity_sessions.workflows import ProcessConversation


async def run_comparison(
    client: Client,
    mode: str,
    task_queue: str,
    known_workers: dict[str, bool],
    workflows: int,
) -> None:
    console = Console()
    if mode == "compare":
        affinity_modes = [False, True]
    elif mode == "on":
        affinity_modes = [True]
    else:
        affinity_modes = [False]
    for affinity_enabled in affinity_modes:

        async def run_workflow(index: int) -> WorkflowResult:
            workflow_id = (
                f"{'on' if affinity_enabled else 'off'}-{uuid.uuid4().hex[:8]}-{index}"
            )
            handle = await client.start_workflow(
                ProcessConversation.run,
                affinity_enabled,
                id=workflow_id,
                task_queue=task_queue,
                execution_timeout=timedelta(minutes=1),
            )
            results = await handle.result()
            history = await handle.fetch_history()
            owners = {
                event.workflow_task_started_event_attributes.identity
                for event in history.events
                if event.HasField("workflow_task_started_event_attributes")
            }
            return WorkflowResult(workflow_id, results, owners)

        runs = await asyncio.gather(
            *(run_workflow(index + 1) for index in range(workflows))
        )
        print_results(affinity_enabled, runs, known_workers, console)


async def run_demo(
    mode: str,
    task_queue: str,
    workers: dict[str, bool],
    workflows: int,
    context_file: Path,
) -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)
    print_worker_configuration(workers, Console())
    # Spawn gives each worker a fresh interpreter, SDK runtime, and private cache.
    context = multiprocessing.get_context("spawn")
    stop = context.Event()
    processes = []
    ready_events = []
    try:
        for identity, session_enabled in workers.items():
            ready = context.Event()
            process = context.Process(
                target=worker_process,
                args=(identity, session_enabled, task_queue, context_file, ready, stop),
            )
            process.start()
            processes.append(process)
            ready_events.append(ready)
        started = await asyncio.gather(
            *(asyncio.to_thread(ready.wait, 30) for ready in ready_events)
        )
        if not all(started):
            raise RuntimeError("A worker failed to start; see its output above")
        await run_comparison(client, mode, task_queue, workers, workflows)
    finally:
        stop.set()
        await asyncio.gather(
            *(asyncio.to_thread(process.join, 15) for process in processes)
        )
        for process in processes:
            if process.is_alive():
                process.terminate()
                await asyncio.to_thread(process.join)
            process.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a worker pool and compare activity affinity and cache reuse."
    )
    parser.add_argument(
        "--affinity", choices=["compare", "on", "off"], default="compare"
    )
    parser.add_argument("--task-queue", default=f"{TASK_QUEUE}-{uuid.uuid4().hex[:8]}")
    parser.add_argument("--session-workers", type=int, default=2)
    parser.add_argument("--activity-workers", type=int, default=0)
    parser.add_argument(
        "--workflows",
        type=int,
        default=1,
        help="Concurrent workflows per affinity mode",
    )
    parser.add_argument(
        "--context-file",
        type=Path,
        default=Path(__file__).with_name("conversation.txt"),
    )
    args = parser.parse_args()
    if args.session_workers < 1:
        parser.error("The demo needs at least one session worker to run workflows")
    if args.workflows < 1:
        parser.error("At least one workflow per mode is required")
    try:
        workers = worker_configuration(args.session_workers, args.activity_workers)
    except ValueError as error:
        parser.error(str(error))
    try:
        asyncio.run(
            run_demo(
                args.affinity,
                args.task_queue,
                workers,
                args.workflows,
                args.context_file,
            )
        )
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
