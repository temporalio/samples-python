# Streaming OpenAI Agents

> **Experimental.** These samples target the streaming hooks added to
> `temporalio.contrib.openai_agents` on the [`contrib/pubsub` branch of
> sdk-python][branch], which is not yet released. Install sdk-python
> from that branch (e.g. `uv pip install -e <path-to-sdk-python>` after
> checking out the branch) to run them locally.

[branch]: https://github.com/temporalio/sdk-python/tree/contrib/pubsub

The OpenAI Agents SDK supports streaming via `Runner.run_streamed`, which
yields `TResponseStreamEvent`s as the model produces them. Inside a
Temporal workflow the model call runs in an activity, so the workflow
cannot iterate the live HTTP stream directly. The plugin's streaming
support runs `model.stream_response()` in the activity and publishes
each event to the workflow's `temporalio.contrib.workflow_stream`. The
publisher coalesces events into batches over `streaming_event_batch_interval`
(default 100ms) before sending them as a signal — call this **buffered
token streaming**: deltas reach external subscribers within a batch
window of being produced, not on every byte. At typical model speeds a
single batch carries multiple tokens, so output arrives in small bursts
rather than glyph-by-glyph — close enough for most UIs, though the
cadence is visible next to a true per-token render. Tune
`streaming_event_batch_interval` to trade signal volume for smoothness.

The two samples here mirror the upstream openai-agents-python basic
streaming examples.

## `stream_text` — buffered text deltas

Adapted from [`examples/basic/stream_text.py`][upstream-text]. Subscribes
to `ResponseTextDeltaEvent`s and prints them as they arrive (batched at
the broker's flush interval, see above).

[upstream-text]: https://github.com/openai/openai-agents-python/blob/main/examples/basic/stream_text.py

```bash
# Terminal 1
uv run openai_agents/streaming/run_worker.py

# Terminal 2
uv run openai_agents/streaming/run_stream_text_workflow.py
```

## `stream_items` — agent-level events with a tool call

Adapted from [`examples/basic/stream_items.py`][upstream-items]. Renders
agent updates, tool calls, tool outputs, and message outputs as a
play-by-play.

[upstream-items]: https://github.com/openai/openai-agents-python/blob/main/examples/basic/stream_items.py

```bash
uv run openai_agents/streaming/run_stream_items_workflow.py
```

## How it works

1. The workflow constructs a `WorkflowStream` from `@workflow.init`.
2. The plugin's `OpenAIAgentsPlugin` is configured with
   `streaming_event_topic="events"`. The plugin routes
   `Runner.run_streamed` calls to `invoke_model_activity_streaming`.
3. Inside that activity, each `TResponseStreamEvent` from the live HTTP
   stream is appended to a list (returned to the workflow when the
   activity completes) **and** published to the stream via
   `WorkflowStreamClient.from_activity()`.
4. The workflow publishes a sentinel to a separate `done` topic right
   before returning, so the subscriber knows the stream is finished.
5. External code subscribes with `WorkflowStreamClient.create(...).subscribe(
   ["events", "done"])` and breaks on the `done` event. We leave
   `result_type` unset and decode events manually because the two
   topics carry different types. The runner also races the consumer
   against `handle.result()` so a workflow failure surfaces as an
   exception rather than blocking the subscriber forever.

In the workflow, `stream_events()` resolves only after the activity
returns, so the workflow itself does not see deltas as they arrive — the
streaming benefit is for external observers. If you want the workflow to
react incrementally, subscribe from a child workflow or activity rather
than from the workflow that hosts the stream.

## Notes

* `streaming_event_topic` defaults to `None` (no publishing). Set it on
  `ModelActivityParameters` to a topic such as `"events"` to publish raw
  stream events.
* Streaming is incompatible with `use_local_activity=True`: local
  activities can neither heartbeat nor send signals back to the workflow.
* The workflow must host a `WorkflowStream`. Without one, the plugin's
  publish signals are unhandled and silently dropped by Temporal.
