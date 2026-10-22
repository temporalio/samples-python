# Activity sessions and a worker-local cache

This experimental sample needs the session SDK from
[sdk-python#1979](https://github.com/temporalio/sdk-python/pull/1979) and the server
from [temporal#12630](https://github.com/temporalio/temporal/pull/12630), with
`system.enableStickyActivityExecution` enabled for your namespace.

The workflow remains simply:

```text
conversation_step(1) → conversation_step(2) → conversation_step(3)
```

Each worker process owns one activity instance and dictionary cache, keyed by
workflow Run ID. A miss reads `conversation.txt`, a stand-in for an external
conversation source. Further activities on the same process reuse that context.
The dictionary and context are not workflow state. A new execution starts cold,
and a new process can reload the context from the file.

Only the activity option changes between the two runs:

```python
"session_options": (
    workflow.ActivitySessionOptions.workflow_session()
    if affinity_enabled
    else None
)
```

## Setup

Build the session SDK with `poe build-develop`. From the samples repository root,
set `SDK_PYTHON` in each terminal to that SDK checkout's `.venv/bin/python`, then
install the sample's Rich display dependency into that environment:

```bash
export SDK_PYTHON=/absolute/path/to/sdk-python/.venv/bin/python
uv pip install --python "$SDK_PYTHON" 'rich>=13,<15'
```

Use this interpreter rather than allowing `uv run` to select the released SDK.
Rich is also declared in this repository's `activity-sessions` dependency group.
The existing SDK environment/profile configuration selects the server and
namespace, defaulting to `localhost:7233` and `default`.

## Launch a pool

In one terminal, choose the worker counts:

```bash
# Ten session-capable workers, each able to run workflows and activities:
"$SDK_PYTHON" -m activity_sessions.pool --session-workers 10

# Alternatively, one session-capable worker and nine normal activity-only workers:
"$SDK_PYTHON" -m activity_sessions.pool --session-workers 1 --activity-workers 9
```

Run only one of these commands at a time. Each child is a fresh Python process
with its own client, runtime, activity instance, and cache. Worker names are
`worker-1` through `worker-N`; session workers come first. Ctrl+C stops the whole
pool, and a child exiting unexpectedly stops the pool rather than silently
leaving a smaller fleet.

All workers use the same logical task queue. Session workers enable
`WorkerSessionOptions()`; activity-only workers register no workflows. This
prevents a workflow requiring session activities from landing on an unsupported
worker. Eager activity execution is disabled.

The default pool is two session workers. A single process can still be started
manually:

```bash
"$SDK_PYTHON" -m activity_sessions.worker --identity worker-1
```

`--activity-only`, `--task-queue`, and `--context-file` are available on the worker.
The pool also accepts `--task-queue` and `--context-file`.

## Run workflows

In another terminal, use the same worker counts:

```bash
# Match the ten-session-worker pool; run ten workflows concurrently per mode:
"$SDK_PYTHON" -m activity_sessions.starter --session-workers 10 --workflows 10

# Or match the one-session/nine-activity-worker pool:
"$SDK_PYTHON" -m activity_sessions.starter \
  --session-workers 1 --activity-workers 9 --workflows 10
```

The default `--affinity compare` runs the ordinary batch first, then the session
batch, without changing worker configuration. **`--workflows 10` means ten per
mode: twenty executions total in comparison mode.** `--affinity on` or `off`
runs only that mode. Every workflow still executes exactly three activities
sequentially.

Rich renders:

1. A worker-configuration table with roles and session support.
2. An execution table showing workflow ID, workflow owner, step, activity worker,
   that worker's session support, and colored cache hit/miss.
3. Per-worker batch totals, including idle workers.

Configuration and idle rows come from the supplied counts, not a health check or
registry. Executing workers' capabilities come from activity results.

With affinity on, each workflow should miss once and hit twice on its owner.
Ordinary routing can scatter activities, or colocate them by chance; the sample
reports the actual result rather than forcing alternation.

## Observe in Temporal UI

A standalone `temporal-server` does not start a UI. Its `7243` port is the HTTP
API, not the UI. For a local server on macOS with Docker Desktop, a separate UI
can be started with:

```bash
docker run --rm --name temporal-session-ui \
  -p 127.0.0.1:8080:8080 \
  -e TEMPORAL_ADDRESS=host.docker.internal:7233 \
  temporalio/ui:latest
```

Open <http://localhost:8080>, select your namespace, and find the workflow IDs
shown in the terminal. This container connects to the custom server; it does not
launch a stock server. Linux Docker host connectivity may require different
network configuration.

## Scope and validation

This demonstrates healthy-worker affinity and cache reuse, not lifetime
isolation, failover, or physical queue provenance. Cache entries live for the
worker process lifetime; production caches need resource limits and eviction.
There are no per-worker queues, cache registry, or artifact protocol.

Unit tests do not require a server. Opt-in tests run the actual pool/starter CLIs
with three workers, ten session workers, and one session/nine activity workers:

```bash
"$SDK_PYTHON" -m pytest tests/activity_sessions -q
TEMPORAL_TEST_ACTIVITY_SESSION_SAMPLE=1 "$SDK_PYTHON" -m pytest \
  tests/activity_sessions -q -s --workflow-environment localhost:7233
```

The integration tests use the existing custom server; they do not start or
reconfigure it.
