# Streaming OpenAI Agents

> **Experimental.** These samples use the streaming support in
> `temporalio.contrib.openai_agents` together with
> `temporalio.contrib.workflow_streams`. Both are experimental and their APIs
> may change in future versions.

*Adapted from the [OpenAI Agents SDK basic examples](https://github.com/openai/openai-agents-python/tree/main/examples/basic)*

Before running these examples, be sure to review the [prerequisites and background on the integration](../README.md).

The OpenAI Agents SDK streams model output via `Runner.run_streamed`, which
yields events as the model produces them. Inside a Temporal workflow the model
call runs in an activity, so the workflow cannot iterate the live HTTP stream
directly. Instead the plugin runs `model.stream_response()` in a streaming
activity, and that activity publishes each event to the workflow's
[`WorkflowStream`](../../workflow_streams/README.md) so external subscribers
see events as they are produced.

Publishing is batched: the activity coalesces events over
`ModelActivityParameters.streaming_batch_interval` (default 100ms) before
signalling the workflow. Call this **buffered token streaming** — deltas reach
subscribers within a batch window of being produced, not on every byte. At
typical model speeds one batch carries several tokens, so output arrives in
small bursts rather than glyph-by-glyph. Lower the interval for smoother
output at the cost of more signals.

Two things to know before reading the samples:

* `streaming_topic` is **required** for `Runner.run_streamed`. If it is unset,
  `run_streamed` raises before scheduling any activity.
* The workflow must host a `WorkflowStream`. It has to be constructed from a
  method named `__init__` — `WorkflowStream` inspects its caller's frame and
  raises otherwise — and `@workflow.init` is what makes the workflow's run
  argument (carrying `stream_state` for continue-as-new) available there.

## Running the Examples

First, start the worker (supports both examples):

```bash
uv run openai_agents/streaming/run_worker.py
```

Then run either example in another terminal.

### `stream_text` — buffered text deltas

Adapted from [`examples/basic/stream_text.py`][upstream-text]. The workflow
just calls `Runner.run_streamed`; the subscriber renders the
`ResponseTextDeltaEvent`s the streaming activity publishes on the `events`
topic.

Subscribers receive **native OpenAI events** (`TResponseStreamEvent`), because
the activity publishes them straight from `Model.stream_response`. That differs
from `stream_events()` inside the workflow, which yields the agents-SDK
`StreamEvent` union — raw model events arrive there wrapped as
`RawResponsesStreamEvent.data`.

[upstream-text]: https://github.com/openai/openai-agents-python/blob/main/examples/basic/stream_text.py

```bash
uv run openai_agents/streaming/run_stream_text_workflow.py
```

### `stream_items` — agent-level events with a tool call

Adapted from [`examples/basic/stream_items.py`][upstream-items]. Renders agent
updates, tool calls, tool outputs, and message outputs as a play-by-play.

The agents SDK builds those higher-level events from the model output, so they
exist only inside the workflow — the streaming activity never sees them. This
workflow therefore does its own publishing: it iterates
`result.stream_events()` and forwards each event of interest to an `items`
topic as a small serializable `ItemEvent`. (The agents-SDK event types carry
the originating `Agent`, which holds tool callables and so cannot be
serialized.) `stream_events()` resolves a turn at a time — each model call is
one activity — so a multi-turn run like this one reaches the subscriber
progressively rather than in one lump.

[upstream-items]: https://github.com/openai/openai-agents-python/blob/main/examples/basic/stream_items.py

```bash
uv run openai_agents/streaming/run_stream_items_workflow.py
```

## How it works

1. The workflow constructs a `WorkflowStream` in `@workflow.init`.
2. `OpenAIAgentsPlugin` is configured with `streaming_topic="events"`, which
   routes `Runner.run_streamed` to `invoke_model_activity_streaming`.
3. Inside that activity each event from the live HTTP stream is both collected
   (returned to the workflow when the activity completes) and published to the
   stream via `WorkflowStreamClient.from_within_activity()`.
4. Just before returning, the workflow publishes a terminator on a separate
   `done` topic, then sleeps briefly so the subscriber's next poll can drain
   the tail of the stream — the log lives in workflow memory and disappears
   when the run completes.
5. External code subscribes with
   `WorkflowStreamClient.create(...).subscribe([...], result_type=RawValue)`
   and breaks on the terminator. `RawValue` keeps the payloads undecoded so
   each topic can be decoded against its own type. If the workflow reaches a
   terminal state without publishing a terminator (a failure, say), the
   iterator exhausts on its own and the following `handle.result()` raises.

In the workflow, `stream_events()` resolves only after the model activity
returns, so the workflow itself does not see deltas as they arrive — the
streaming benefit is for external observers.

## Notes

* Streaming is incompatible with `use_local_activity=True`: local activities
  support neither heartbeats nor the workflow stream signal channel.
* The streaming activity heartbeats on a background task, so set
  `heartbeat_timeout` well below `start_to_close_timeout` to detect a stuck
  model call early.
* Delivery is at-least-once per activity attempt. An attempt that fails
  mid-response leaves its partial events on the stream — they are flushed
  before the failure is reported — and the retry publishes a whole new
  response. `stream_events()` in the workflow only sees the successful attempt,
  so the workflow's return value stays correct while a naive subscriber renders
  the truncated attempt followed by the full one.

  The plugin's streaming activity publishes no retry marker, so subscribers
  detect this in band: every OpenAI stream event carries a `sequence_number`
  that starts at 0 per response, and a number that fails to advance means a new
  attempt. `run_stream_text_workflow.py` prints a notice at that seam;
  `workflow_streams/run_llm.py` shows the fuller treatment, where an activity
  you own publishes an explicit `RetryEvent` from `activity.info().attempt` and
  the consumer erases the failed attempt's output.
