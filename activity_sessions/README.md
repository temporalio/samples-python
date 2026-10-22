# Activity sessions and a worker-local cache

This experimental sample needs the session SDK from
[sdk-python#1979](https://github.com/temporalio/sdk-python/pull/1979) and the server
from [temporal#12630](https://github.com/temporalio/temporal/pull/12630), with
`system.enableStickyActivityExecution` enabled for your namespace.

The workflow is simply:

```text
conversation_step(1) → conversation_step(2) → conversation_step(3)
```

Each worker process has its own `ConversationActivities` instance and dictionary.
The activity looks up conversation context by workflow Run ID. On a miss it reads
`conversation.txt`, our stand-in for loading context from an external source.
Subsequent activities on that process reuse the cached context.

The cache is not workflow state. The workflow only receives step number, worker
identity, session capability, and hit/miss. A new process can load the context
again from the file. Each comparison execution has a new Run ID and starts cold.

The only difference between the two runs is the **activity** option:

```python
"session_options": (
    workflow.ActivitySessionOptions.workflow_session()
    if affinity_enabled
    else None
)
```

## Run

Build the session SDK with `poe build-develop`. From this repository root, in each
terminal, set `SDK_PYTHON` to that SDK checkout's `.venv/bin/python`. Use this
interpreter rather than letting `uv run` select the released SDK dependency.
Connection configuration uses the existing SDK environment/profile settings and
defaults to `localhost:7233`.

Start a separate worker process in each of two terminals:

```bash
"$SDK_PYTHON" -m activity_sessions.worker --identity worker-1
"$SDK_PYTHON" -m activity_sessions.worker --identity worker-2
```

Both register the same workflow and activity and enable `WorkerSessionOptions()`.
Eager activity dispatch is disabled. In another terminal:

```bash
"$SDK_PYTHON" -m activity_sessions.starter
```

The starter runs affinity off, then on, with the workers unchanged. It prints the
workflow worker from history, each activity's worker and cache result, and a
per-worker summary with **Session support ON/OFF**.

With affinity on, expect one miss followed by two hits on the workflow owner.
Without affinity, context may be loaded on several workers. Ordinary routing may
also colocate every activity by chance; the sample reports the observed result.

## Optional activity-only workers

All workflow-capable workers must enable session support. To add normal activity
competition, start processes that register only the activity:

```bash
"$SDK_PYTHON" -m activity_sessions.worker --identity worker-3 --activity-only
"$SDK_PYTHON" -m activity_sessions.starter --activity-workers worker-3
```

The `--session-workers` and `--activity-workers` arguments identify known workers
for zero-execution rows. Capabilities for workers that actually execute activities
come from their results; this table is not a worker health check or registry.
Repeat the activity-only command with more unique identities for a larger pool.

Ctrl+C or SIGTERM shuts down a worker. No per-worker queues, cache registry,
artifact protocol, or external services are required. `--context-file` can select
another shared context file. This demonstrates healthy-worker affinity and cache
reuse, not lifetime isolation, failover, or physical queue provenance.

## Validation

Cache/report tests do not need a server. The opt-in test runs actual worker
processes and the starter CLI against the custom server:

```bash
"$SDK_PYTHON" -m pytest tests/activity_sessions -q
TEMPORAL_TEST_ACTIVITY_SESSION_SAMPLE=1 "$SDK_PYTHON" -m pytest \
  tests/activity_sessions -q -s --workflow-environment localhost:7233
```
