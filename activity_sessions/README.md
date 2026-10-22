# Activity sessions and a worker-local cache

This sample shows how activity affinity lets a workflow reuse conversation context
cached in its worker's memory, without managing per-worker task queues.

Each workflow calls three regular activities sequentially:

```text
conversation_step(1) → conversation_step(2) → conversation_step(3)
```

Each worker runs in a separate process with its own dictionary cache, keyed by
workflow Run ID. A cache miss loads `conversation.txt`, standing in for an external
conversation source. The context is **worker-local, not workflow state**, and can
be reloaded if absent.

With affinity **on**, activities use
`workflow.ActivitySessionOptions.workflow_session()`: expect one MISS followed by
two HITs on the workflow's worker. With affinity **off**, activities may execute
on different workers and load the context separately. They may also colocate by
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

This starts two session-capable worker processes, runs one workflow with affinity
off and another with affinity on, prints the results, and shuts down the workers.
Ctrl+C also requests shutdown of all workers.

For a larger pool, choose either:

```bash
# Ten session-capable workers; ten workflows per affinity mode.
"$SDK_PYTHON" -m activity_sessions.run --session-workers 10 --workflows 10

# One session-capable worker plus nine ordinary activity-only workers.
"$SDK_PYTHON" -m activity_sessions.run \
  --session-workers 1 --activity-workers 9 --workflows 10
```

`--workflows` is the concurrent workflow count **per mode**: the commands above
run twenty workflows total. Use `--affinity on` or `--affinity off` to run just one
mode. Workers stay unchanged between the two batches, and eager activity
execution is disabled. Only session-capable workers register workflows.

The tables show worker configuration, which worker executed each workflow/activity,
cache HITs/MISSes, and per-worker totals including idle workers.

Each invocation uses a unique shared task queue to avoid interference from other
runs. Optional `--task-queue` and `--context-file` arguments override the defaults.
Run with `--help` to see all options.
