# Workflow Streams

> **Experimental.** These samples use
> `temporalio.contrib.workflow_streams`, which ships in
> `temporalio>=1.27.0`. The module is considered experimental and its
> API may change in future versions.

`temporalio.contrib.workflow_streams` lets a workflow host a durable,
offset-addressed event channel. The workflow holds an append-only log;
external clients (activities, starters, BFFs) publish to topics via
signals and subscribe via long-poll updates. This packages the
boilerplate — batching, offset tracking, topic filtering, continue-as-new
hand-off — into a reusable stream.

This directory has four scenarios sharing one Worker, plus a fifth
LLM-streaming scenario on its own Worker (see
[Scenario 5 — LLM streaming](#scenario-5--llm-streaming) below for why
it's separate).

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
  task runs alongside; when the publisher is done it emits an in-band
  sentinel headline (`__done__`) into the stream, then signals
  `HubWorkflow.close`. The subscriber breaks on the sentinel and
  exits its `async for`. This is the shape that fits a backend
  service or scheduled job pushing events into a workflow it didn't
  itself start.

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

## Scenario 5 — LLM streaming

* `workflows/llm_workflow.py` — a workflow that hosts a
  `WorkflowStream` and runs `stream_completion` as a single activity.
  The workflow itself does no streaming; the activity owns the
  non-deterministic OpenAI call.
* `activities/llm_activity.py` — calls
  `openai.AsyncOpenAI().chat.completions.create(stream=True)`,
  publishes each token chunk as a `TextDelta` on the `delta` topic,
  the final accumulated text on the `complete` topic, and a
  `RetryEvent` on the `retry` topic when running on attempt > 1.
* `run_llm.py` — subscribes to all three topics, renders deltas to
  the terminal as they arrive, and on a `retry` event uses ANSI
  escapes to rewind the printed output before the retried attempt
  starts re-publishing.
* `run_llm_worker.py` — separate worker on its own task queue
  (`workflow-stream-llm-task-queue`), registering only `LLMWorkflow`
  and `stream_completion`. This isolates the `openai` dependency and
  the `OPENAI_API_KEY` requirement to this one scenario.

This scenario is split out for two reasons. First, it needs an extra
dependency (`openai`) and a secret (`OPENAI_API_KEY`) — putting it on
the main worker would force every other scenario to set up an OpenAI
key. Second, killing the LLM worker mid-stream is the easiest way to
demonstrate retry handling, and you don't want the same `Ctrl-C` to
interrupt the other four scenarios' worker.

Setup:

```bash
uv sync --group llm-stream
export OPENAI_API_KEY=...
```

Run:

```bash
# Terminal 1: LLM worker (its own task queue)
uv run workflow_streams/run_llm_worker.py

# Terminal 2:
uv run workflow_streams/run_llm.py
```

To trigger the retry path, kill the LLM worker in Terminal 1
(`Ctrl-C`) while output is streaming, then start it again. The
activity's next attempt sends a `RetryEvent` first; the consumer
clears its on-screen output via ANSI escapes and re-renders from
scratch.

## Ending the stream

`WorkflowStreamClient.subscribe()` is a long-poll loop — it does not
exit on its own when the host workflow completes. Two things have to
happen at the end of a streamed workflow for clean shutdown:

1. **An in-band terminator that subscribers recognize.** Each scenario
   here sends one before the workflow exits:
   - `OrderWorkflow` and `PipelineWorkflow` publish a "complete"
     status / stage event; consumers break on it.
   - `run_external_publisher.py` publishes a sentinel
     `NewsEvent(headline="__done__")` immediately before signaling
     `HubWorkflow.close`; the consumer breaks on the sentinel.
   - `TickerWorkflow`'s final tick (`n == count - 1`) is the
     terminator; subscribers break when they see it. `keep_last`
     guarantees that final offset survives the last truncation, so
     even slow consumers reach it.

2. **A short hold-open in the workflow before returning** so that the
   final publish gets fetched. Items published in the same workflow
   task that returns from `@workflow.run` are abandoned: the
   in-memory log dies with the workflow, and the next subscriber
   poll lands on a completed workflow. Each workflow here ends with

   ```python
   await workflow.sleep(timedelta(milliseconds=500))
   return ...
   ```

   which gives subscribers in their `poll_cooldown` interval time to
   issue one more poll. With both pieces in place, subscribers
   receive the terminator, break out of their `async for`, and stop
   polling — by the time the workflow exits there are no in-flight
   poll handlers, so the SDK does not warn about unfinished
   handlers.

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

Expected output on the reconnecting subscriber side. Each line carries
a stats column on the left (`proc`, `avail`, `pend`) and a phase /
event message on the right; a background poller emits a `·` heartbeat
once a second. Offsets are continuous across the disconnect — no
events lost, none duplicated:

```
proc= 0  avail= 0  pend= 0     │ started workflow-stream-pipeline-...
proc= 0  avail= 1  pend= 1     │ [phase 1] connecting
proc= 1  avail= 1  pend= 0     │   offset= 0  stage=validating
proc= 2  avail= 2  pend= 0     │   offset= 1  stage=loading data
proc= 2  avail= 2  pend= 0     │ [phase 1] disconnecting
proc= 2  avail= 3  pend= 1     │ ·
proc= 2  avail= 3  pend= 1     │ ·
proc= 2  avail= 4  pend= 2     │ ·
proc= 2  avail= 4  pend= 2     │ [phase 2] reconnecting
proc= 3  avail= 4  pend= 1     │   offset= 2  stage=transforming
proc= 4  avail= 4  pend= 0     │   offset= 3  stage=writing output
proc= 5  avail= 5  pend= 0     │   offset= 4  stage=verifying
proc= 6  avail= 6  pend= 0     │   offset= 5  stage=complete
proc= 6  avail= 6  pend= 0     │ workflow result: pipeline ... done
```

## Notes

* **Subscriber start position.** `subscribe(...)` without `from_offset`
  starts at the stream's current base offset and follows live — older
  events that have been truncated, or that arrived before the
  subscribe call, are not replayed. Pass `from_offset=N` to resume
  from a known position (see `run_reconnecting_subscriber.py`); the
  iterator skips forward to the current base if `N` has been
  truncated.
* **Continue-as-new.** Every `*Input` dataclass carries
  `stream_state: WorkflowStreamState | None = None`. To survive
  continue-as-new without losing buffered items, capture the workflow's
  stream state and pass it to the next run via
  `WorkflowStream(prior_state=...)` in `@workflow.init`. The samples
  declare the field for completeness; none of them actually trigger
  continue-as-new.
