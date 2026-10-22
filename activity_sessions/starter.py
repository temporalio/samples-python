import argparse
import asyncio
import uuid
from collections.abc import Sequence
from datetime import timedelta

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from activity_sessions import TASK_QUEUE, StepResult
from activity_sessions.workflows import ProcessConversation


def print_results(
    affinity_enabled: bool,
    results: Sequence[StepResult],
    workflow_workers: set[str],
    known_workers: dict[str, bool],
) -> None:
    print(f"\nActivity affinity: {'ON' if affinity_enabled else 'OFF'}")
    print(f"Workflow-task worker(s): {', '.join(sorted(workflow_workers))}")
    print(f"{'Step':<6}{'Activity worker':<22}{'Session support':<18}Cache")
    for result in results:
        print(
            f"{result.step:<6}{result.worker_identity:<22}"
            f"{'ON' if result.session_enabled else 'OFF':<18}"
            f"{'HIT' if result.cache_hit else 'MISS'}"
        )
    print(
        f"\n{'Worker':<22}{'Session support':<18}{'Steps':<8}{'Hits':<8}Misses / context loads"
    )
    roles = {
        **known_workers,
        **{item.worker_identity: item.session_enabled for item in results},
    }
    for identity, session_enabled in sorted(roles.items()):
        steps = [item for item in results if item.worker_identity == identity]
        hits = sum(item.cache_hit for item in steps)
        print(
            f"{identity:<22}{'ON' if session_enabled else 'OFF':<18}"
            f"{len(steps):<8}{hits:<8}{len(steps) - hits}"
        )
    if affinity_enabled:
        assert len(results) == 3
        assert len(workflow_workers) == 1
        assert all(item.worker_identity in workflow_workers for item in results)
        assert [item.cache_hit for item in results] == [False, True, True]
        print("Verified: one context load, then two cache hits on the workflow worker.")
    else:
        print(
            "Ordinary placement is not guaranteed; this run may also colocate by chance."
        )


async def run_comparison(
    mode: str, task_queue: str, known_workers: dict[str, bool]
) -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)
    if mode == "compare":
        affinity_modes = [False, True]
    elif mode == "on":
        affinity_modes = [True]
    else:
        affinity_modes = [False]
    for affinity_enabled in affinity_modes:
        handle = await client.start_workflow(
            ProcessConversation.run,
            affinity_enabled,
            id=f"conversation-{uuid.uuid4()}",
            task_queue=task_queue,
            execution_timeout=timedelta(minutes=1),
        )
        results = await handle.result()
        history = await handle.fetch_history()
        workflow_workers = {
            event.workflow_task_started_event_attributes.identity
            for event in history.events
            if event.HasField("workflow_task_started_event_attributes")
        }
        print_results(affinity_enabled, results, workflow_workers, known_workers)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--affinity", choices=["compare", "on", "off"], default="compare"
    )
    parser.add_argument("--task-queue", default=TASK_QUEUE)
    parser.add_argument(
        "--session-workers", nargs="+", default=["worker-1", "worker-2"]
    )
    parser.add_argument("--activity-workers", nargs="*", default=[])
    args = parser.parse_args()
    known_workers = {
        **{identity: True for identity in args.session_workers},
        **{identity: False for identity in args.activity_workers},
    }
    asyncio.run(run_comparison(args.affinity, args.task_queue, known_workers))


if __name__ == "__main__":
    main()
