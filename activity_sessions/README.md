# Activity sessions and a worker-local cache

This sample shows how activity affinity lets a workflow reuse conversation context
cached in its worker's memory, without managing per-worker task queues.

Each workflow calls `conversation_step` sequentially (five times by default). Each
worker runs in a separate process with its own dictionary cache, keyed by workflow
Run ID. A cache miss sleeps for `--load-seconds` (default 1s), standing in for a
slow fetch of conversation history; a hit is instant. The context is
**worker-local, not workflow state**, and can be reloaded if absent.

With affinity **on**, activities use
`workflow.ActivitySessionOptions.workflow_session()`: each workflow loads its
context once and every later step hits the cache on the same worker. With affinity
**off**, steps spread across the pool, so the same context is loaded on several
workers and workflows take several times longer. Steps may still colocate by
chance; ordinary routing does not guarantee either outcome.

## Prerequisites

1. Run the server from [temporal#12630](https://github.com/temporalio/temporal/pull/12630),
   with the `default` namespace and `system.enableStickyActivityExecution` enabled.
2. Build the SDK from [sdk-python#1979](https://github.com/temporalio/sdk-python/pull/1979)
   by running `poe build-develop` in that SDK checkout.
3. From the **samples repository root**, select the built SDK's interpreter and
   install Rich for the result tables:

   ```bash
   export SDK_PYTHON=/absolute/path/to/sdk-python/.venv/bin/python
   uv pip install --python "$SDK_PYTHON" 'rich>=13,<15'
   ```

Use this interpreter for the commands below; the released SDK does not provide
the experimental session API. The sample connects to `localhost:7233`, namespace
`default`, unless overridden by `TEMPORAL_ADDRESS` / `TEMPORAL_NAMESPACE` or SDK
profile configuration.

## Run

From the **samples repository root**, run:

```bash
"$SDK_PYTHON" -m activity_sessions.run
```

This starts four session-capable worker processes, runs 20 concurrent workflows
with affinity off and then 20 with affinity on, and shuts down the workers.

While a batch runs, a live view shows each worker's cache filling up and a
placement strip per workflow: `●` is a context load (miss), `○` a cache hit, `◌`
a load in progress, and the number/color is the worker that ran the step. The
final summary prints both batches side by side, followed by an impact table:
context loads, cache copies per workflow, time spent loading, and workflow latency.
Pass `--no-live` (or redirect output) to print only the summary.

Useful options (run with `--help` for all):

```bash
# More workers and steps make ordinary placement scatter even more.
"$SDK_PYTHON" -m activity_sessions.run --session-workers 8 --steps 10

# One session-capable worker plus three activity-only workers.
"$SDK_PYTHON" -m activity_sessions.run --session-workers 1 --activity-workers 3

# Run only one mode, with a faster simulated load.
"$SDK_PYTHON" -m activity_sessions.run --affinity on --load-seconds 0.2
```

`--workflows` is the concurrent workflow count **per mode**. Only session-capable
workers register the workflow; activity-only workers never receive session
activities. Workflows start only after every worker is polling, eager activity
execution is disabled, and each invocation uses a unique task queue. The command
exits non-zero if any affinity-on workflow did not load once and reuse its cache on
a single worker.
