# Workflow Streams

> **Experimental.** These samples target the
> `temporalio.contrib.workflow_streams` module on the
> [`contrib/pubsub` branch of sdk-python][branch], which is not yet
> released. To run them locally, install sdk-python from that branch
> (e.g. `uv pip install -e <path-to-sdk-python>` after checking out the
> branch).

[branch]: https://github.com/temporalio/sdk-python/tree/contrib/pubsub

`temporalio.contrib.workflow_streams` lets a workflow host a durable,
offset-addressed event channel. The workflow holds an append-only log;
external clients (activities, starters, BFFs) publish to topics via
signals and subscribe via long-poll updates. This packages the
boilerplate — batching, offset tracking, topic filtering, continue-as-new
hand-off — into a reusable stream.

This directory has two scenarios sharing one Worker.

**Scenario 1 — basic publish/subscribe with heterogeneous topics:**

* `workflows/order_workflow.py` — a workflow that hosts a
  `WorkflowStream` and publishes status events as it processes an order.
* `activities/payment_activity.py` — an activity that publishes
  intermediate progress to the stream via
  `WorkflowStreamClient.from_within_activity()`.
* `run_publisher.py` — starts the workflow, subscribes to both topics,
  decodes each by `item.topic`, and prints events as they arrive.

**Scenario 2 — reconnecting subscriber:**

* `workflows/pipeline_workflow.py` — a multi-stage pipeline that
  publishes stage transitions over ~10 seconds, leaving room for a
  consumer to disconnect and reconnect mid-run.
* `run_reconnecting_subscriber.py` — connects, reads a couple of
  events, persists `item.offset + 1` to disk, "disconnects," then
  reopens a fresh client and resumes via `subscribe(from_offset=...)`.
  This is the central Workflow Streams use case: a consumer can
  disappear (page refresh, server restart, laptop closed) and resume
  later without missing events or seeing duplicates.

**Scenario 3 — external (non-Activity) publisher:**

* `workflows/hub_workflow.py` — a passive workflow that does no work
  of its own; it exists only to host a `WorkflowStream` and shut down
  when signaled.
* `run_external_publisher.py` — starts the hub, then publishes events
  into it from a plain Python coroutine using
  `WorkflowStreamClient.create(client, workflow_id)`. A subscriber
  task runs alongside; when the publisher is done it signals
  `HubWorkflow.close`, the workflow's run finishes, and the
  subscriber's iterator exits normally. This is the shape that fits a
  backend service or scheduled job pushing events into a workflow it
  didn't itself start.

**Scenario 4 — bounded log via `truncate()`:**

* `workflows/ticker_workflow.py` — a long-running workflow that
  publishes events at a fixed cadence and calls
  `self.stream.truncate(...)` periodically to bound log growth, keeping
  only the most recent N entries.
* `run_truncating_ticker.py` — runs a fast subscriber and a slow
  subscriber side by side. The fast one keeps up and sees every offset
  in order; the slow one sleeps between iterations, falls behind a
  truncation, and silently jumps forward to the new base offset. The
  output makes the trade visible: bounded log size in exchange for
  intermediate events being invisible to slow consumers.

`run_worker.py` registers all four workflows and the activity.

## Run it

```bash
# Terminal 1: worker
uv run workflow_streams/run_worker.py

# Terminal 2: pick a scenario
uv run workflow_streams/run_publisher.py
# or
uv run workflow_streams/run_reconnecting_subscriber.py
# or
uv run workflow_streams/run_external_publisher.py
# or
uv run workflow_streams/run_truncating_ticker.py
```

Expected output on the basic publisher side:

```
[status] received: order=order-1
[progress] charging card...
[progress] card charged
[status] shipped: order=order-1
[progress] charge id: charge-order-1
[status] complete: order=order-1
workflow result: charge-order-1
```

Expected output on the reconnecting subscriber side (note the offsets
are continuous across the disconnect — no events lost, none duplicated):

```
[phase 1] connecting and reading first few events
  offset= 0  stage=validating
  offset= 1  stage=loading data
[phase 1] persisted resume offset=2 -> /tmp/...; disconnecting

[phase 2] reconnecting and resuming from persisted offset
  offset= 2  stage=transforming
  offset= 3  stage=writing output
  offset= 4  stage=verifying
  offset= 5  stage=complete

workflow result: pipeline workflow-stream-pipeline-... done
```
