# Activity sessions: reuse worker-local conversation data

**Experimental demo.** Requires the Python SDK session branch
([sdk-python#1979](https://github.com/temporalio/sdk-python/pull/1979)) and a server
built from [temporal#12630](https://github.com/temporalio/temporal/pull/12630).
The ordinary released SDK and stock downloaded dev server are not substitutes.

The same `ProcessConversation` workflow calls the same regular activity five times
sequentially. The starter runs it with activity affinity off, then on, without
changing the worker configuration.

```python
session_options = (
    workflow.ActivitySessionOptions.workflow_session()
    if request.affinity_enabled
    else None
)
```

Each step consumes the preceding step's output. Only a small content-addressed
reference passes through workflow history. Conversation data lives in a shared,
file-backed mock external store. Each worker process owns a private dictionary
cache, scoped by workflow Run ID and artifact reference.

- A miss reads the artifact from the shared store.
- Every step persists its output before returning its reference, then caches that
  output locally.
- The next step on the same process can reuse the output without another read.
- A different process or a restarted worker can read the persisted output instead.

The cache is not workflow state and is not reconstructed by replay. It is an
optimization, not the only copy of the conversation. This is not an implementation
of SDK `ExternalStorage`; it makes the avoided artifact reads explicit.

## Prerequisites

Start the custom server with `system.enableStickyActivityExecution` enabled for
your namespace. Create the namespace if necessary. For example, after starting a
fresh in-memory server:

```bash
temporal --address localhost:7233 operator namespace create --namespace default
```

Build the session SDK checkout following its `poe build-develop` instructions.
From the samples repository root, use that checkout's interpreter so the released
SDK dependency in this repository does not replace the experimental SDK:

```bash
export SDK_PYTHON=/absolute/path/to/sdk-python/.venv/bin/python
```

All processes must use that same SDK build. The sample uses the repository's
standard `ClientConfig.load_client_connect_config()` configuration, defaulting to
`localhost:7233`. Authentication and namespace can be supplied via the existing
environment configuration mechanism.

## Start two worker processes

In terminal 1, from the repository root:

```bash
"$SDK_PYTHON" -m activity_sessions.worker --identity worker-1
```

In terminal 2:

```bash
"$SDK_PYTHON" -m activity_sessions.worker --identity worker-2
```

Both workers register the workflow and activity, enable
`WorkerSessionOptions()`, use fixed activity capacity, and disable eager dispatch.
Each prints its PID and each activity's cache result as it runs. Each invocation
creates its own client, Temporal runtime, activity instance, and cache.

The shared directory defaults to `activity_sessions/.data` and is ignored by Git.
Use the same `--store-dir` and `--task-queue` on every worker and the starter.
The filesystem must be shared; this mock setup is intended for processes on one
machine, not separate hosts.

## Run the comparison

In terminal 3:

```bash
"$SDK_PYTHON" -m activity_sessions.starter
```

Each execution has a different Run ID, so both start with a cold cache even when
the initial artifact has the same content. The starter prints:

- Workflow-task worker identities obtained from history.
- Per-step executing identity, cache hit/miss, artifact reads, and artifact writes.
- A per-worker table including **Session support ON/OFF** and zero-execution rows.

For example, with affinity enabled:

```text
Step  Activity worker  Cache  Artifact reads  Artifact writes
1     worker-1         MISS   1               1
2     worker-1         HIT    0               1
3     worker-1         HIT    0               1
4     worker-1         HIT    0               1
5     worker-1         HIT    0               1

Worker    Session support  Steps  Hits  Misses  Artifact reads  Artifact writes
worker-1  ON               5      4     1       1               5
worker-2  ON               0      0     0       0               0
```

Every step still writes its output for durability. Affinity saves input reads; it
does not eliminate those writes. Counts exclude the starter's seed/verification
I/O and worker-roster I/O.

**Ordinary routing may also colocate every activity.** The sample reports actual
placement and does not force alternation or assert a disabled run must have more
misses. Run again or use a larger pool for more observations:

```bash
"$SDK_PYTHON" -m activity_sessions.starter --affinity off --steps 10
"$SDK_PYTHON" -m activity_sessions.starter --affinity on --steps 10
```

## Optional mixed pool

Keep the session-capable workers above, then start additional activity-only
processes with unique identities:

```bash
"$SDK_PYTHON" -m activity_sessions.worker --identity worker-3 --activity-only
```

Repeat with `worker-4` through `worker-10` if desired. These workers register the
same activity on the same normal queue but do not run workflows or poll sticky
activity queues. Their table rows show **Session support OFF**.

All workflow-capable workers must enable session support: the current protocol
does not select a session-capable worker based on the workflow input.

## Shutdown and limitations

Use Ctrl+C or SIGTERM for graceful shutdown. A small local roster records each
worker's configured identity, role, PID, and queue so idle workers can appear in
the table. It is not a health check. Graceful shutdown removes the registration;
a hard crash can leave a stale entry. Use a fresh `--store-dir` for a fresh demo
after a crash rather than trusting stale registrations.

This demonstrates the normal, healthy-worker path. It does not demonstrate
single-session lifetime isolation, stable destinations, worker-loss recovery,
sticky timeout fallback, or Continue-As-New placement. Cache entries are retained
for the process lifetime; production code needs eviction and resource limits.

The result table observes worker colocation, not the physical queue of each poll.
No per-worker task queue names are managed by application code.

## Tests

```bash
"$SDK_PYTHON" -m pytest tests/activity_sessions -q
```

The cache/storage/report tests do not require a server. The opt-in SDK/server test
launches independent worker processes in three-worker and ten-worker configurations
(two session workers plus activity-only workers), runs the starter CLI, checks
both modes, and shuts down its own worker processes:

```bash
TEMPORAL_TEST_ACTIVITY_SESSION_SAMPLE=1 "$SDK_PYTHON" -m pytest \
  tests/activity_sessions -q -s --workflow-environment localhost:7233
```

This test requires the custom server, namespace gate, and session SDK. It is
skipped by default; it does not start or reconfigure the custom server.
