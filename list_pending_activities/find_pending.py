"""Find workflows with pending activities and save results locally.

All filters are optional — use any combination to narrow the search.

Authentication:
    API key:  export TEMPORAL_API_KEY="your-api-key"
    mTLS:     Falls back to certs if TEMPORAL_API_KEY is not set.

Usage:
    python find_pending.py
    python find_pending.py --task-queue my-queue
    python find_pending.py --workflow-type MyWorkflow --status Running
    python find_pending.py --start-time-after "2026-03-01T00:00:00Z" --start-time-before "2026-03-25T00:00:00Z"
    python find_pending.py --close-time-after "2026-03-20T00:00:00Z"
"""

import argparse
import asyncio
import json
import os
from datetime import datetime

from temporalio.client import Client
from temporalio.service import TLSConfig

DEFAULT_NAMESPACE = "deepika-test-namespace.a2dd6" # namespace - <ns>.<account-id>
DEFAULT_API_HOST = "us-east-1.aws.api.temporal.io:7233" # regional endpoint for your namespace
DEFAULT_MTLS_HOST = "deepika-test-namespace.a2dd6.tmprl.cloud:7233" # namespace endpoint for your namespace
DEFAULT_CERTS_DIR = "/Users/deepikaawasthi/temporal/temporal-certs" # certs directory


def resolve_api_key() -> str | None:
    """Read API key from TEMPORAL_API_KEY env var, or return None to fall back to mTLS."""
    return os.environ.get("TEMPORAL_API_KEY")


async def create_client(api_key: str | None = None) -> Client:
    namespace = os.environ.get("TEMPORAL_NAMESPACE", DEFAULT_NAMESPACE)

    if api_key:
        target_host = os.environ.get("TEMPORAL_ADDRESS", DEFAULT_API_HOST)
        print(f"Authenticating with API key to {target_host}")
        return await Client.connect(
            target_host,
            namespace=namespace,
            api_key=api_key,
            tls=True,
        )

    # Fall back to mTLS
    target_host = os.environ.get("TEMPORAL_ADDRESS", DEFAULT_MTLS_HOST)
    certs_dir = os.environ.get("TEMPORAL_CERTS_DIR", DEFAULT_CERTS_DIR)
    print(f"Authenticating with mTLS to {target_host}")

    with open(os.path.join(certs_dir, "client.pem"), "rb") as f:
        client_cert = f.read()
    with open(os.path.join(certs_dir, "client.key"), "rb") as f:
        client_key = f.read()

    return await Client.connect(
        target_host,
        namespace=namespace,
        tls=TLSConfig(
            client_cert=client_cert,
            client_private_key=client_key,
        ),
    )


def build_query(
    task_queue: str | None = None,
    workflow_type: str | None = None,
    status: str | None = None,
    start_time_after: str | None = None,
    start_time_before: str | None = None,
    close_time_after: str | None = None,
    close_time_before: str | None = None,
) -> str:
    """Build a visibility query from optional filters."""
    clauses = []

    if task_queue:
        clauses.append(f'TaskQueue="{task_queue}"')
    if workflow_type:
        clauses.append(f'WorkflowType="{workflow_type}"')
    if status:
        clauses.append(f'ExecutionStatus="{status}"')
    if start_time_after:
        clauses.append(f'StartTime>="{start_time_after}"')
    if start_time_before:
        clauses.append(f'StartTime<="{start_time_before}"')
    if close_time_after:
        clauses.append(f'CloseTime>="{close_time_after}"')
    if close_time_before:
        clauses.append(f'CloseTime<="{close_time_before}"')

    return " AND ".join(clauses) if clauses else ""


async def find_workflows_with_pending_activities(
    client: Client,
    query: str,
) -> list[dict]:
    """List workflows matching the query, describe each, return those with pending activities."""

    results = []

    async for wf in client.list_workflows(query=query or None):
        handle = client.get_workflow_handle(wf.id, run_id=wf.run_id)
        desc = await handle.describe()

        pending = desc.raw_description.pending_activities
        if not pending:
            continue

        activities_info = []
        for pa in pending:
            activities_info.append(
                {
                    "activity_id": pa.activity_id,
                    "activity_type": pa.activity_type.name,
                    "state": str(pa.state),
                    "attempt": pa.attempt,
                }
            )

        parent_exec = desc.raw_description.parent_execution
        parent_id = parent_exec.workflow_id if parent_exec else None

        results.append(
            {
                "workflow_id": wf.id,
                "run_id": wf.run_id,
                "workflow_type": str(getattr(wf, "workflow_type", "")),
                "parent_workflow_id": parent_id,
                "pending_activity_count": len(pending),
                "pending_activities": activities_info,
            }
        )

    return results


def save_results(results: list[dict], query: str) -> str:
    """Save results to a JSON file in the output/ directory. Returns the file path."""
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, f"pending_activities_{timestamp}.json")

    with open(filepath, "w") as f:
        json.dump(
            {
                "generated_at": datetime.now().isoformat(),
                "query_used": query,
                "total_workflows": len(results),
                "workflows": results,
            },
            f,
            indent=2,
        )

    return filepath


def print_results(results: list[dict]) -> None:
    print("-" * 80)
    for entry in results:
        print(f"Workflow ID   : {entry['workflow_id']}")
        print(f"Run ID        : {entry['run_id']}")
        print(f"Workflow Type : {entry['workflow_type']}")
        print(f"Parent WF ID  : {entry['parent_workflow_id'] or '(none — top-level)'}")
        print(f"Pending Count : {entry['pending_activity_count']}")
        for act in entry["pending_activities"]:
            print(
                f"  - Activity ID: {act['activity_id']}, "
                f"Type: {act['activity_type']}, "
                f"State: {act['state']}, "
                f"Attempt: {act['attempt']}"
            )
        print("-" * 80)


async def main():
    parser = argparse.ArgumentParser(
        description="Find workflows with pending activities. All filters are optional."
    )
    parser.add_argument("--task-queue", default=None, help="Filter by task queue name")
    parser.add_argument("--workflow-type", default=None, help="Filter by workflow type name")
    parser.add_argument(
        "--status",
        default=None,
        choices=["Running", "Completed", "Failed", "Canceled", "Terminated", "ContinuedAsNew", "TimedOut"],
        help="Filter by execution status (default: all statuses)",
    )
    parser.add_argument(
        "--start-time-after",
        default=None,
        help='Workflows started at or after this time (ISO 8601, e.g. "2026-03-01T00:00:00Z")',
    )
    parser.add_argument(
        "--start-time-before",
        default=None,
        help='Workflows started at or before this time (ISO 8601, e.g. "2026-03-25T00:00:00Z")',
    )
    parser.add_argument(
        "--close-time-after",
        default=None,
        help='Workflows closed at or after this time (ISO 8601, e.g. "2026-03-20T00:00:00Z")',
    )
    parser.add_argument(
        "--close-time-before",
        default=None,
        help='Workflows closed at or before this time (ISO 8601, e.g. "2026-03-25T00:00:00Z")',
    )
    args = parser.parse_args()

    query = build_query(
        task_queue=args.task_queue,
        workflow_type=args.workflow_type,
        status=args.status,
        start_time_after=args.start_time_after,
        start_time_before=args.start_time_before,
        close_time_after=args.close_time_after,
        close_time_before=args.close_time_before,
    )

    print(f"Query: {query or '(no filters — scanning all workflows)'}\n")

    api_key = resolve_api_key()
    client = await create_client(api_key=api_key)
    results = await find_workflows_with_pending_activities(client, query)

    if not results:
        print("No workflows with pending activities found.")
        return

    print(f"Found {len(results)} workflow(s) with pending activities:\n")
    print_results(results)

    filepath = save_results(results, query)
    print(f"\nResults saved to: {filepath}")


if __name__ == "__main__":
    asyncio.run(main())
