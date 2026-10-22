import argparse
import asyncio
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from temporalio.client import Client, WorkflowHistory
from temporalio.envconfig import ClientConfig

from activity_sessions import TASK_QUEUE
from activity_sessions.models import (
    ConversationContext,
    ConversationRequest,
    StepResult,
    WorkerRegistration,
)
from activity_sessions.storage import FileArtifactStore
from activity_sessions.workflows import ProcessConversation


@dataclass
class WorkerSummary:
    identity: str
    session_enabled: bool
    steps: int = 0
    hits: int = 0
    misses: int = 0
    artifact_reads: int = 0
    artifact_writes: int = 0


def summarize_workers(
    results: Sequence[StepResult], roster: Sequence[WorkerRegistration]
) -> list[WorkerSummary]:
    summaries = {
        item.identity: WorkerSummary(item.identity, item.session_enabled)
        for item in roster
    }
    for result in results:
        summary = summaries.setdefault(
            result.worker_identity,
            WorkerSummary(result.worker_identity, result.session_enabled),
        )
        if summary.session_enabled != result.session_enabled:
            raise ValueError(
                f"Worker {summary.identity!r} changed session capability during the run"
            )
        summary.steps += 1
        summary.hits += int(result.cache_hit)
        summary.misses += int(not result.cache_hit)
        summary.artifact_reads += result.artifact_reads
        summary.artifact_writes += result.artifact_writes
    return sorted(summaries.values(), key=lambda item: item.identity)


def format_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    all_rows = [headers, *rows]
    widths = [max(len(row[index]) for row in all_rows) for index in range(len(headers))]
    return "\n".join(
        "  ".join(value.ljust(width) for value, width in zip(row, widths))
        for row in all_rows
    )


def print_comparison(
    affinity_enabled: bool,
    run_id: str,
    results: Sequence[StepResult],
    history: WorkflowHistory,
    roster: Sequence[WorkerRegistration],
) -> None:
    owners = {
        event.workflow_task_started_event_attributes.identity
        for event in history.events
        if event.HasField("workflow_task_started_event_attributes")
    }
    print(f"\nActivity affinity: {'ON' if affinity_enabled else 'OFF'}")
    print(f"Workflow Run ID: {run_id}")
    print(f"Workflow-task worker(s): {', '.join(sorted(owners))}")
    print(
        format_table(
            ["Step", "Activity worker", "Cache", "Artifact reads", "Artifact writes"],
            [
                [
                    str(result.step),
                    result.worker_identity,
                    "HIT" if result.cache_hit else "MISS",
                    str(result.artifact_reads),
                    str(result.artifact_writes),
                ]
                for result in results
            ],
        )
    )
    print("\nPer-worker totals for this run (idle rows use the local worker roster):")
    print(
        format_table(
            [
                "Worker",
                "Session support",
                "Steps",
                "Hits",
                "Misses",
                "Artifact reads",
                "Artifact writes",
            ],
            [
                [
                    item.identity,
                    "ON" if item.session_enabled else "OFF",
                    str(item.steps),
                    str(item.hits),
                    str(item.misses),
                    str(item.artifact_reads),
                    str(item.artifact_writes),
                ]
                for item in summarize_workers(results, roster)
            ],
        )
    )
    print(
        f"Workers executing activities: {len({result.worker_identity for result in results})}; "
        f"artifact reads: {sum(result.artifact_reads for result in results)}; "
        f"artifact writes: {sum(result.artifact_writes for result in results)}"
    )
    if affinity_enabled:
        if len(owners) != 1 or any(
            result.worker_identity not in owners for result in results
        ):
            raise RuntimeError(
                "Session activities did not remain on one workflow owner"
            )
        if results[0].cache_hit or any(not result.cache_hit for result in results[1:]):
            raise RuntimeError(
                "Expected a cold first step followed by local cache hits"
            )
        print(
            "Verified: activities stayed with the workflow owner; subsequent steps reused its cache."
        )
    elif len({result.worker_identity for result in results}) == 1:
        print(
            "Ordinary routing colocated these activities by chance; placement is not guaranteed."
        )


async def run_comparison(
    mode: str, steps: int, task_queue: str, store_directory: Path
) -> None:
    if steps < 1:
        raise ValueError("At least one step is required")
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)
    store = FileArtifactStore(store_directory)
    roster = store.list_workers(task_queue)
    if not any(item.session_enabled for item in roster):
        raise RuntimeError(
            "Start at least one session-capable worker using the same store and task queue"
        )
    input_ref = store.write(
        ConversationContext(
            messages=["Hydrated conversation context from the mock external store."]
        )
    )
    modes = [False, True] if mode == "compare" else [mode == "on"]
    for affinity_enabled in modes:
        handle = await client.start_workflow(
            ProcessConversation.run,
            ConversationRequest(input_ref, affinity_enabled, steps),
            id=f"conversation-{'affine' if affinity_enabled else 'ordinary'}-{uuid.uuid4()}",
            task_queue=task_queue,
            execution_timeout=timedelta(minutes=2),
        )
        results = await handle.result()
        if len(results) != steps:
            raise RuntimeError(f"Expected {steps} step results, got {len(results)}")
        final_context = store.read(results[-1].output_ref)
        if final_context.completed_steps != list(range(1, steps + 1)):
            raise RuntimeError(
                "Persisted output does not contain the complete conversation pipeline"
            )
        print_comparison(
            affinity_enabled,
            handle.first_execution_run_id or "",
            results,
            await handle.fetch_history(),
            store.list_workers(task_queue),
        )
    print(
        "\nRead/write totals count activity artifact I/O, excluding starter and worker-roster I/O."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare ordinary and workflow-session activity caches."
    )
    parser.add_argument(
        "--affinity", choices=["compare", "on", "off"], default="compare"
    )
    parser.add_argument("--steps", type=int, default=5)
    parser.add_argument("--task-queue", default=TASK_QUEUE)
    parser.add_argument(
        "--store-dir", type=Path, default=Path("activity_sessions/.data")
    )
    args = parser.parse_args()
    asyncio.run(
        run_comparison(args.affinity, args.steps, args.task_queue, args.store_dir)
    )


if __name__ == "__main__":
    main()
