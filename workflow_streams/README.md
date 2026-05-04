# Workflow Streams

> **Experimental.** These samples use
> `temporalio.contrib.workflow_streams`, which ships in
> `temporalio>=1.27.0`. The module is considered experimental and its
> API may change in future versions.

`temporalio.contrib.workflow_streams` lets a workflow host a durable,
offset-addressed event channel. The workflow holds an append-only log;
external clients (activities, starters, web backends) publish to topics via
signals and subscribe via long-poll updates. This packages the
boilerplate — batching, offset tracking, topic filtering,
continue-as-new hand-off — into a reusable stream.

This directory has five scenarios. The first four share one worker;
the fifth has its own worker because it needs the `openai` package
and an `OPENAI_API_KEY`.

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
  events, "disconnects," then reopens a fresh client and resumes via
  `subscribe(from_offset=...)`. This is the central Workflow Streams
  use case: a consumer can disappear (page refresh, server restart,
  laptop closed) and resume later without missing events or seeing
  duplicates.

**Scenario 3 — external (non-Activity) publisher:**

* `workflows/hub_workflow.py` — a passive workflow that does no work
  of its own; it exists only to host a `WorkflowStream` and shut down
  when signaled.
* `run_external_publisher.py` — starts the hub, then publishes events
  into it from a plain Python coroutine using
  `WorkflowStreamClient.create(client, workflow_id)`. A subscriber
  task runs alongside; when the publisher is done it emits a sentinel
  event and signals `HubWorkflow.close`. The shape that fits a
  backend service or scheduled job pushing events into a workflow it
  didn't itself start.

**Scenario 4 — bounded log via `truncate()`:**

* `workflows/ticker_workflow.py` — a long-running workflow that
  publishes events at a fixed cadence and calls
  `self.stream.truncate(...)` periodically to bound log growth,
  keeping only the most recent N entries.
* `run_truncating_ticker.py` — runs a fast subscriber and a slow
  subscriber side by side. The fast one keeps up and sees every
  offset in order; the slow one falls behind a truncation and
  silently jumps forward to the new base offset. The output makes
  the trade visible: bounded log size in exchange for intermediate
  events being invisible to slow consumers.

**Scenario 5 — LLM streaming:**

* `workflows/llm_workflow.py` — hosts a `WorkflowStream` and runs
  `stream_completion` as a single activity. The workflow itself
  does no streaming; the activity owns the non-deterministic OpenAI
  call.
* `activities/llm_activity.py` — calls
  `openai.AsyncOpenAI().chat.completions.create(stream=True)`,
  publishes each token chunk on the `delta` topic, the final
  accumulated text on `complete`, and a `RetryEvent` on `retry`
  when running on attempt > 1.
* `run_llm.py` — subscribes to all three topics, renders deltas to
  the terminal as they arrive, and on a `retry` event uses ANSI
  escapes to rewind the printed output before the retried attempt
  re-publishes.

Scenario 5 runs on its own worker (`run_llm_worker.py`, on
`workflow-stream-llm-task-queue`) because it needs the `openai`
dependency and an `OPENAI_API_KEY`, and because killing this worker
mid-stream is the easiest way to demonstrate retry handling without
disrupting the other four scenarios.

## Run it

For scenarios 1–4, start the shared worker:

```bash
uv run workflow_streams/run_worker.py
```

For scenario 5, install the extra, export the key, and start the
LLM worker:

```bash
uv sync --group llm-stream
export OPENAI_API_KEY=...
uv run workflow_streams/run_llm_worker.py
```

Then in another terminal, pick a scenario:

```bash
uv run workflow_streams/run_publisher.py              # scenario 1
uv run workflow_streams/run_reconnecting_subscriber.py  # scenario 2
uv run workflow_streams/run_external_publisher.py     # scenario 3
uv run workflow_streams/run_truncating_ticker.py      # scenario 4
uv run workflow_streams/run_llm.py                    # scenario 5
```

To exercise scenario 5's retry path, kill `run_llm_worker.py`
(`Ctrl-C`) while output is streaming and start it again. The
activity's next attempt sends a `RetryEvent` first; the consumer
clears its on-screen output via ANSI escapes and re-renders from
scratch.
