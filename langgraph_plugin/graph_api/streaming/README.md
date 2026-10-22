# Streaming (Graph API)

Streams a LangGraph run to an external client while the workflow is still running, using Temporal's durable, offset-addressed [`WorkflowStream`](https://github.com/temporalio/sdk-python/tree/main/temporalio/contrib/workflow_streams). The graph writes a short story about a topic and emits both fine-grained tokens and node-completion progress on separate topics.

## What This Sample Demonstrates

- **Node token streaming** — the `write_story` node calls LangGraph's `get_stream_writer()` to emit tokens. The plugin's `streaming_topic="tokens"` routes those writes onto the `"tokens"` topic.
- **Workflow-side `astream` publish** — the workflow drives the graph with `app.astream(...)` and publishes each node-completion chunk onto a `"progress"` topic it owns.
- A single client subscribing to all topics and demultiplexing on `item.topic`.
- Waiting for the client to acknowledge (via signal) before completing, since the stream disappears when the workflow ends.
- **Idempotent consumption** — each token chunk carries a monotonic sequence id so the client can dedupe, because streaming is at-least-once per activity attempt (a retried node re-runs and re-publishes its writes).

## Running the Sample

Prerequisites: `uv sync --group langgraph` and a running Temporal dev server (`temporal server start-dev`).

```bash
# Terminal 1
uv run langgraph_plugin/graph_api/streaming/run_worker.py

# Terminal 2
uv run langgraph_plugin/graph_api/streaming/run_workflow.py
```

## Files

| File | Description |
|------|-------------|
| `workflow.py` | Graph node functions, graph definition, and `StreamingWorkflow` that publishes to the stream |
| `run_worker.py` | Registers graph with `LangGraphPlugin` (`streaming_topic="tokens"`), starts worker |
| `run_workflow.py` | Starts the workflow, subscribes to the stream, prints tokens and progress, then acks |
