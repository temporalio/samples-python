# Streaming

Strands' model stream produces a sequence of `StreamEvent`s (token deltas, tool-use chunks, message-stop, etc.). With `TemporalAgent(streaming_topic="events")`, the model activity publishes each chunk onto a workflow-hosted `WorkflowStream`; external subscribers read it via `WorkflowStreamClient`. Chunks are batched on `streaming_batch_interval` (default 100ms) to keep activity overhead low.

## What This Sample Demonstrates

- Hosting a `WorkflowStream` on a workflow
- `TemporalAgent(streaming_topic=...)` publishing model events
- An external subscriber reading `StreamEvent`s in real time via `WorkflowStreamClient`

## Running the Sample

```bash
# Terminal 1
uv run strands_plugin/streaming/run_worker.py

# Terminal 2
uv run strands_plugin/streaming/run_workflow.py
```

The starter prints text deltas as they arrive, then the final workflow result.

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `StreamingWorkflow` hosting `WorkflowStream` + `TemporalAgent(streaming_topic="events")` |
| `run_worker.py` | Registers `StrandsPlugin`, starts the worker |
| `run_workflow.py` | Starts the workflow and subscribes to the `events` topic |
