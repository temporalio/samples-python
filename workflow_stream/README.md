# Workflow Streams

> **Experimental.** These samples target the
> `temporalio.contrib.workflow_stream` module on the
> [`contrib/pubsub` branch of sdk-python][branch], which is not yet
> released. To run them locally, install sdk-python from that branch
> (e.g. `uv pip install -e <path-to-sdk-python>` after checking out the
> branch).

[branch]: https://github.com/temporalio/sdk-python/tree/contrib/pubsub

`temporalio.contrib.workflow_stream` lets a workflow host a durable,
offset-addressed event channel. The workflow holds an append-only log;
external clients (activities, starters, BFFs) publish to topics via
signals and subscribe via long-poll updates. This packages the
boilerplate — batching, offset tracking, topic filtering, continue-as-new
hand-off — into a reusable stream.

This directory has a minimal end-to-end example:

* `workflows/order_workflow.py` — a workflow that hosts a
  `WorkflowStream` and publishes status events as it processes an order.
* `activities/payment_activity.py` — an activity that publishes
  intermediate progress to the stream via
  `WorkflowStreamClient.from_activity()`.
* `run_worker.py` — registers the workflow and activity.
* `run_publisher.py` — starts the workflow, then prints subscribed
  events as they arrive.

## Run it

```bash
# Terminal 1: worker
uv run workflow_stream/run_worker.py

# Terminal 2: starter + subscriber
uv run workflow_stream/run_publisher.py
```

Expected output on the publisher side, with events streaming in as the
workflow progresses:

```
[status] received: order=order-1
[progress] charging card...
[progress] card charged
[status] shipped: order=order-1
[progress] charge id: charge-order-1
[status] complete: order=order-1
workflow result: charge-order-1
```
