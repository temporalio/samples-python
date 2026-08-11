# Streaming

Stream model output from a durable workflow to external subscribers in real
time, while keeping the durable workflow result identical to the non-streaming
path. Streaming is async-only, so the workflow drives the plugin's
`TemporalModel.astream(...)` directly — the same seam a full Deep Agent's model
calls go through.

Constructing the plugin with `DeepAgentsPlugin(streaming_topic=...)` flips model
dispatch from `deepagents.invoke_model` to `deepagents.invoke_model_streaming`.
The streaming activity coalesces chunk batches and publishes them to a
`temporalio.contrib.workflow_streams` topic; the aggregated final message is
still returned to the workflow.

Streaming is async-only, so the workflow drives an explicit
`TemporalModel.astream(...)` and hosts a `WorkflowStream` so subscribers can
attach by workflow id. The starter subscribes to the topic and prints chunks as
they arrive.

## What This Sample Demonstrates

- `DeepAgentsPlugin(streaming_topic=...)` to enable streaming dispatch
- Hosting a `WorkflowStream` in the workflow and driving `TemporalModel.astream`
- A client subscribing via `WorkflowStreamClient` and decoding `AIMessageChunk`
  batches with `langchain_core.load.load`

## Running the Sample

Prerequisites: Python >= 3.11 with the [suite setup](../README.md#prerequisites)
applied (interim plugin install), an `ANTHROPIC_API_KEY` in your
environment, and a running Temporal dev server (`temporal server start-dev`).

> The experimental plugin is not in the `deepagents` group — install it as shown
> in the [suite README](../README.md#prerequisites) and run with `--no-sync`, or
> a bare `uv run`/`uv sync` re-syncs the environment and uninstalls it.

```bash
# Terminal 1
uv run --no-sync deepagents_plugin/streaming/run_worker.py

# Terminal 2
uv run --no-sync deepagents_plugin/streaming/run_workflow.py
```

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `StreamingWorkflow` hosting a `WorkflowStream`, driving `astream` |
| `run_worker.py` | Adds `DeepAgentsPlugin(streaming_topic=...)`, starts the worker |
| `run_workflow.py` | Starts the workflow and prints streamed chunks live |
