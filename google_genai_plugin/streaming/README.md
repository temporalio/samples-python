# Streaming

Forward Gemini model output to an external subscriber in real time.
`TemporalAsyncClient(streaming_topic="gemini")` publishes each
`generate_content_stream` chunk onto a workflow-hosted `WorkflowStream` as it
arrives. A subscriber connects with `WorkflowStreamClient` and reads the topic
live while the workflow runs durably.

## What This Sample Demonstrates

- `TemporalAsyncClient(streaming_topic=...)` publishing chunks to a topic
- Hosting a `WorkflowStream` in `@workflow.init` (required for streaming)
- Consuming the stream externally via `WorkflowStreamClient.subscribe(...)`
- Holding the workflow open on a signal so the subscriber can drain the stream

## Running the Sample

Prerequisites: install dependencies, set `GOOGLE_API_KEY`, and start a Temporal
dev server. See the [suite README](../README.md).

```bash
# Terminal 1
uv run google_genai_plugin/streaming/run_worker.py

# Terminal 2
uv run google_genai_plugin/streaming/run_workflow.py
```

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `StreamingWorkflow` — streams chunks to the `gemini` topic |
| `run_worker.py` | Registers `GoogleGenAIPlugin`, starts the worker |
| `run_workflow.py` | Starts the workflow and consumes the stream live |
