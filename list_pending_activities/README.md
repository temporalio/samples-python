# List Pending Activities

A command-line tool that queries a Temporal Cloud namespace to find all workflows with pending activities. Supports optional filters and saves results to a local JSON file.

## How it works

1. Builds a [visibility query](https://docs.temporal.io/visibility#list-filter) from the optional filters you provide
2. Calls `client.list_workflows()` to retrieve matching workflows
3. Calls `handle.describe()` on each workflow to check for pending activities
4. Prints results to the console and saves them to `output/pending_activities_<timestamp>.json`

Both parent and child workflows are found — child workflows are independent executions in the visibility store and are queried the same way.

## Authentication

The script supports two auth modes. If `TEMPORAL_API_KEY` is set, it uses API key auth via the regional endpoint. Otherwise it falls back to mTLS via the namespace endpoint.

**API key:**
```bash
export TEMPORAL_API_KEY="your-api-key"
python find_pending.py
```

**mTLS (default):**
```bash
python find_pending.py
```

Requires `client.pem` and `client.key` in the certs directory.

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `TEMPORAL_API_KEY` | (not set) | API key for auth. If set, uses the regional API endpoint. |
| `TEMPORAL_NAMESPACE` | `deepika-test-namespace.a2dd6` | Namespace to query. |
| `TEMPORAL_ADDRESS` | Regional or namespace endpoint | Overrides the target host for either auth mode. |
| `TEMPORAL_CERTS_DIR` | `/Users/deepikaawasthi/temporal/temporal-certs` | Directory containing `client.pem` and `client.key` for mTLS. |

## Usage

All flags are optional — use any combination to narrow the search.

```bash
# No filters — scans all workflows in the namespace
python find_pending.py

# Filter by task queue
python find_pending.py --task-queue my-queue

# Filter by workflow type
python find_pending.py --workflow-type MyWorkflow

# Filter by execution status
python find_pending.py --status Running

# Filter by start time range
python find_pending.py --start-time-after "2026-03-01T00:00:00Z" --start-time-before "2026-03-25T00:00:00Z"

# Filter by close time range
python find_pending.py --close-time-after "2026-03-20T00:00:00Z" --close-time-before "2026-03-25T00:00:00Z"

# Combine any filters
python find_pending.py --task-queue my-queue --workflow-type MyWorkflow --status Running --start-time-after "2026-03-20T00:00:00Z"
```

### Available filters

| Flag | Visibility Query | Description |
|---|---|---|
| `--task-queue` | `TaskQueue="..."` | Filter by task queue name |
| `--workflow-type` | `WorkflowType="..."` | Filter by workflow type name |
| `--status` | `ExecutionStatus="..."` | Filter by status: `Running`, `Completed`, `Failed`, `Canceled`, `Terminated`, `ContinuedAsNew`, `TimedOut` |
| `--start-time-after` | `StartTime>="..."` | Workflows started at or after this time |
| `--start-time-before` | `StartTime<="..."` | Workflows started at or before this time |
| `--close-time-after` | `CloseTime>="..."` | Workflows closed at or after this time |
| `--close-time-before` | `CloseTime<="..."` | Workflows closed at or before this time |

All times are in ISO 8601 format (e.g. `2026-03-01T00:00:00Z`).

## Output

Results are printed to the console and saved to `output/pending_activities_<timestamp>.json`:

```json
{
  "generated_at": "2026-03-25T10:04:12.832303",
  "query_used": "WorkflowType=\"PendingActivitiesWorkflow\" AND ExecutionStatus=\"Running\"",
  "total_workflows": 1,
  "workflows": [
    {
      "workflow_id": "hello-pending-activities-workflow",
      "run_id": "019d25f3-65f4-7c71-9c86-acfb68faec15",
      "pending_activity_count": 3,
      "pending_activities": [
        {
          "activity_id": "1",
          "activity_type": "say_hello",
          "state": "1",
          "attempt": 1
        }
      ]
    }
  ]
}
```

## Notes

- With no filters the script scans **all** workflows in the namespace. Use filters to narrow the scope for large namespaces.
- Only workflows with at least one pending activity appear in the output.
- The `output/` directory is created automatically on first run.
