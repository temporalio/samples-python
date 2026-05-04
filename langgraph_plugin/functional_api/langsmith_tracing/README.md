# LangSmith Tracing (Functional API)

Demonstrates combining `LangGraphPlugin` (durable task execution) with Temporal's `LangSmithPlugin` for full tracing of LLM calls through Temporal workflows, using LangGraph's `@task` and `@entrypoint` decorators.

## What This Sample Demonstrates

- Using `LangSmithPlugin` on the Temporal client for automatic trace propagation
- Using `LangGraphPlugin` on the Worker for durable LangGraph execution
- `@traceable` in three places: on the `@task` (Activity) itself, on a helper called from inside the `@task`, and on a helper called from inside the `@entrypoint` (Workflow)
- Both plugins working together: durability + observability

## How It Works

1. The Temporal client is created with `LangSmithPlugin(add_temporal_runs=True)`.
2. A Worker registers the `chat` task with `LangGraphPlugin`.
3. When the Workflow runs, the `chat` task executes as a Temporal Activity.
4. `@traceable` decorators emit trace data to LangSmith for the task, an in-task helper, and an in-entrypoint helper.

## Running the Sample

Prerequisites: `uv sync --group langgraph` and a running Temporal dev server (`temporal server start-dev`).

```bash
export ANTHROPIC_API_KEY='your-key'
export LANGCHAIN_API_KEY='your-key'

uv run langgraph_plugin/functional_api/langsmith_tracing/main.py
```

Traces will appear in your [LangSmith](https://smith.langchain.com/) dashboard.

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `@traceable` chat task + helpers, `@entrypoint`, and `ChatFunctionalWorkflow` |
| `main.py` | Starts a Worker and executes the Workflow in a single process |
