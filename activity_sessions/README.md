# Activity sessions and a worker-local cache

This sample shows how activity affinity lets a workflow reuse conversation history
cached in its worker's memory, without managing per-worker task queues.

Each workflow is a conversation: it calls `conversation_step(0)`,
`conversation_step(1)`, ... sequentially (six turns by default). Turn `n` needs
every earlier turn `0..n-1`, then produces turn `n`. Each worker runs in a
separate process with its own dictionary cache of the turns it holds, keyed by
workflow Run ID. Before running a turn, a worker fetches only the earlier turns it
is missing, sleeping `--fetch-seconds` (default 0.5s) per turn to stand in for an
external conversation store. Turn 0 needs no history. The history is
**worker-local, not workflow state**, and can be refetched if absent.

With affinity **on**, activities use
`workflow.ActivitySessionOptions.workflow_session()`: the workflow's worker
produced every earlier turn itself, so it never fetches. With affinity **off**,
turns spread across the pool. A worker that ran turn 0 and then returns for turn 2
must fetch turn 1, and a cold worker at turn `n` fetches all `n` earlier turns, so
fetch time grows with how stale each worker is. Turns may still colocate by
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

While a batch runs, a live view shows how far each worker holds every
conversation (`03:t4` means workflow 3 through turn 4) and a placement strip per
workflow. In the strip, `○2` means worker 2 ran the turn with every earlier turn
already cached, `●2(3)` means worker 2 first fetched 3 missing turns, and `◌` is
a fetch in progress; color also identifies the worker. The final summary prints
both batches side by side, followed by an impact table: turns fetched, steps that
had to fetch, time spent fetching, cached turns across the fleet, and workflow
latency.
Pass `--no-live` (or redirect output) to print only the summary.

Useful options (run with `--help` for all):

```bash
# More workers and longer conversations make ordinary placement fetch even more.
"$SDK_PYTHON" -m activity_sessions.run --session-workers 8 --steps 10

# One session-capable worker plus three activity-only workers.
"$SDK_PYTHON" -m activity_sessions.run --session-workers 1 --activity-workers 3

# Run only one mode, with a faster simulated fetch.
"$SDK_PYTHON" -m activity_sessions.run --affinity off --fetch-seconds 0.1
```

`--workflows` is the concurrent workflow count **per mode**. Only session-capable
workers register the workflow; activity-only workers never receive session
activities. Workflows start only after every worker is polling, eager activity
execution is disabled, and each invocation uses a unique task queue. The command
exits non-zero if any affinity-on workflow ran on more than one worker or fetched
any turn.
