# Streaming — Token Streaming to an External Consumer

A workflow that hosts a `WorkflowStream` and uses
`TemporalModel("gemini-2.5-flash", streaming_topic="responses")` with
`RunConfig(streaming_mode=StreamingMode.SSE)`. The streaming model activity
publishes raw `LlmResponse` chunks to the topic as they arrive; the starter
subscribes via `WorkflowStreamClient` and prints chunks as they come in, then
prints the final result.

> Streaming support in the plugin is experimental and may change.

Before running, review the [prerequisites in the suite README](../README.md)
(Temporal dev server, `uv sync --group google-adk`, and
`export GOOGLE_API_KEY=...`).

## Running

Start the worker in one terminal:

```bash
uv run python -m google_adk_agents.streaming.run_worker
```

Then start the workflow in another terminal:

```bash
uv run python -m google_adk_agents.streaming.run_streaming_workflow
```

## What to expect

The starter asks for a short story and prints the response token-by-token as the
model streams it, then prints the assembled final result.

## In the Temporal UI

Open the workflow `google-adk-agents-streaming-workflow-id`. The history shows
an `invoke_model_streaming` activity (instead of `invoke_model`). That activity
calls the model with streaming enabled and publishes each chunk to the
`responses` topic, which is what the starter subscribes to.
