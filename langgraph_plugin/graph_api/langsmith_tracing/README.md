# LangSmith Tracing (Graph API)

Demonstrates combining the LangGraph plugin (durable execution) with Temporal's LangSmith plugin (observability) for full tracing of LLM calls through Temporal workflows.

## What This Sample Demonstrates

- Using `LangSmithPlugin` on the Temporal client for automatic trace propagation
- Using `LangGraphPlugin` on the Worker for durable LangGraph execution
- `@traceable` in three places: on the Activity itself, on a helper called from inside the Activity, and on a helper called from inside the Workflow
- Both plugins working together: durability + observability

## How It Works

1. The Temporal client is created with `LangSmithPlugin(add_temporal_runs=True)`.
2. A Worker is created with `LangGraphPlugin` wrapping the chat graph.
3. When the Workflow runs, the `chat` node executes as a Temporal Activity.
4. `@traceable` decorators emit trace data to LangSmith for the Activity, an in-Activity helper, and an in-Workflow helper.
5. The `LangSmithPlugin` adds Temporal-specific metadata to the traces.

## Running the Sample

Prerequisites: `uv sync --group langgraph` and a running Temporal dev server (`temporal server start-dev`).

```bash
export ANTHROPIC_API_KEY='your-key'
export LANGCHAIN_API_KEY='your-key'

uv run langgraph_plugin/graph_api/langsmith_tracing/main.py
```

Traces will appear in your [LangSmith](https://smith.langchain.com/) dashboard.

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `@traceable` chat node + helpers, graph definition, and `ChatWorkflow` |
| `main.py` | Starts a Worker and executes the Workflow in a single process |
