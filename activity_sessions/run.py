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


async def run_workflows(
    client: Client,
    affinity_enabled: bool,
    task_queue: str,
    known_workers: dict[str, bool],
    workflows: int,
) -> None:
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
    print_results(affinity_enabled, runs, known_workers)


async def main() -> None:
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

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)
    print_worker_configuration(workers, Console())
    # Spawn gives each worker a fresh interpreter, SDK runtime, and private cache.
    context = multiprocessing.get_context("spawn")
    stop = context.Event()
    processes = []
    try:
        for identity, session_enabled in workers.items():
            process = context.Process(
                target=worker_process,
                args=(
                    identity,
                    session_enabled,
                    args.task_queue,
                    args.context_file,
                    stop,
                ),
            )
            process.start()
            processes.append(process)

        if args.affinity == "compare":
            affinity_modes = [False, True]
        else:
            affinity_modes = [args.affinity == "on"]
        for affinity_enabled in affinity_modes:
            await run_workflows(
                client,
                affinity_enabled,
                args.task_queue,
                workers,
                args.workflows,
            )
    finally:
        stop.set()
        await asyncio.gather(
            *(asyncio.to_thread(process.join) for process in processes)
        )
        for process in processes:
            process.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
