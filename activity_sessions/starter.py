import argparse
import asyncio
import uuid
from datetime import timedelta

from rich.console import Console
from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from activity_sessions import TASK_QUEUE, worker_configuration
from activity_sessions.display import (
    WorkflowResult,
    print_results,
    print_worker_configuration,
)
from activity_sessions.workflows import ProcessConversation


async def run_comparison(
    mode: str, task_queue: str, known_workers: dict[str, bool], workflows: int = 1
) -> None:
    if workflows < 1:
        raise ValueError("At least one workflow per mode is required")
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)
    console = Console()
    print_worker_configuration(known_workers, console)
    console.print(
        "[dim]Configuration comes from the supplied counts, not a health check.[/dim]"
    )
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--affinity", choices=["compare", "on", "off"], default="compare"
    )
    parser.add_argument("--task-queue", default=TASK_QUEUE)
    parser.add_argument("--session-workers", type=int, default=2)
    parser.add_argument("--activity-workers", type=int, default=0)
    parser.add_argument(
        "--workflows",
        type=int,
        default=1,
        help="Concurrent workflows per affinity mode",
    )
    args = parser.parse_args()
    if args.session_workers < 1:
        parser.error("The demo needs at least one session worker to run workflows")
    try:
        workers = worker_configuration(args.session_workers, args.activity_workers)
        asyncio.run(
            run_comparison(args.affinity, args.task_queue, workers, args.workflows)
        )
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
