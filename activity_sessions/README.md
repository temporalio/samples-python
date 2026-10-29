# Activity sessions and a worker-local cache

This sample shows how activity sessions keep a workflow's activities on one worker,
so they can reuse state cached in that worker's memory without per-worker task
queues.

Each workflow is a conversation: it calls `conversation_step(0)`,
`conversation_step(1)`, ... sequentially. Turn `n` needs every earlier turn. Each
worker runs in a separate process with its own cache of the turns it holds; before
running a turn, a worker fetches the earlier turns it is missing, sleeping
`--fetch-seconds` per turn to stand in for an external conversation store.

The workflow, activity, and worker code is shared; only whether the workflow opens
a session and how workers are configured changes:

| Mode | Workflow | Workers |
| --- | --- | --- |
| `none` | No session: ordinary task-queue routing | `WorkerSessionConfig()` |
| `affinity` | Turns run inside `workflow.activity_session(ActivitySessionOptions(placement=UseWorkflowSession()))` | `WorkerSessionConfig()` |
| `single-session` | Same as `affinity` | `WorkerSessionConfig(admission=SingleSessionAdmission(stable_identity=...))` |

## Prerequisites

1. Run a server built from the `shivam/agentcore-single-session` branch of
   [temporalio/temporal](https://github.com/temporalio/temporal), with the
   `default` namespace and `system.enableStickyActivityExecution` enabled.
2. Build the SDK from [sdk-python#1979](https://github.com/temporalio/sdk-python/pull/1979)
   by running `poe build-develop` in that SDK checkout, then select its
   interpreter:

   ```bash
   export SDK_PYTHON=/absolute/path/to/sdk-python/.venv/bin/python
   ```

The released SDK does not provide the experimental session API. The sample
connects to `localhost:7233`, namespace `default`, unless overridden by
`TEMPORAL_ADDRESS` / `TEMPORAL_NAMESPACE` or SDK profile configuration. Run the
commands below from the **samples repository root**.

## Compare modes

```bash
"$SDK_PYTHON" -m activity_sessions.affinity                  # none and affinity
"$SDK_PYTHON" -m activity_sessions.affinity --modes none affinity single-session
```

Each mode runs `--workflows` (default 8) workflows on a fresh worker fleet:
`--workers` (default 4) workers for `none` and `affinity`, one worker per workflow
for `single-session`. It then compares turns fetched, time spent fetching, and the
most workflows any one worker served:

- `none`: turns spread across the fleet, so workers keep fetching turns they missed.
- `affinity`: every turn runs on the workflow's worker, which already holds the
  earlier turns, so nothing is fetched. Workers serve many workflows.
- `single-session`: the same reuse, with each worker serving exactly one workflow.

The command exits non-zero if `affinity` or `single-session` workflows run on more
than one worker or fetch, or if a `single-session` worker serves more than one
workflow.

## Tests

```bash
"$SDK_PYTHON" -m pytest tests/activity_sessions
```
