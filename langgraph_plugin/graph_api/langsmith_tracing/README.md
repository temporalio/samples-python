# LangSmith Tracing (Graph API)

Demonstrates combining the LangGraph plugin (durable execution) with Temporal's LangSmith plugin (observability) for full tracing of LLM calls through Temporal workflows.

## What This Sample Demonstrates

- Using `LangSmithPlugin` on the Temporal client for automatic trace propagation
- Using `LangGraphPlugin` on the worker for durable LangGraph execution
- `@traceable` decorators for fine-grained LangSmith tracing within activities
- Both plugins working together: durability + observability

## How It Works

1. The Temporal client is created with `LangSmithPlugin(add_temporal_runs=True)`.
2. The worker is created with `LangGraphPlugin` wrapping the chat graph.
3. When the workflow runs, the `chat` node executes as a Temporal activity.
4. The `@traceable` decorator on the activity sends trace data to LangSmith.
5. The `LangSmithPlugin` adds Temporal-specific metadata to the traces.

## Running the Sample

Prerequisites: `uv sync --group langgraph` and a running Temporal dev server.

```bash
export ANTHROPIC_API_KEY='your-key'
export LANGCHAIN_API_KEY='your-key'

# Terminal 1
uv run langgraph_plugin/graph_api/langsmith_tracing/run_worker.py

# Terminal 2
uv run langgraph_plugin/graph_api/langsmith_tracing/run_workflow.py
```

Traces will appear in your [LangSmith](https://smith.langchain.com/) dashboard.

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `@traceable` chat node, graph definition, and `ChatWorkflow` |
| `run_worker.py` | Creates client with `LangSmithPlugin`, worker with `LangGraphPlugin` |
| `run_workflow.py` | Creates client with `LangSmithPlugin`, executes workflow |
