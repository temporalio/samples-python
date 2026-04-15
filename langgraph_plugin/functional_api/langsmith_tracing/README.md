# LangSmith Tracing (Functional API)

Same pattern as the Graph API version, using `@task` and `@entrypoint` decorators.

## What This Sample Demonstrates

- Combining `LangSmithPlugin` (observability) with `LangGraphPlugin` (durability)
- `@traceable` decorator on a `@task` for LangSmith tracing of LLM calls
- Both plugins working together in the Functional API style

## How It Works

1. The Temporal client is created with `LangSmithPlugin(add_temporal_runs=True)`.
2. The worker registers the `chat` task with `LangGraphPlugin`.
3. When the workflow runs, the `chat` task executes as a Temporal activity.
4. The `@traceable` decorator sends trace data to LangSmith.

## Running the Sample

Prerequisites: `uv sync --group langgraph` and a running Temporal dev server.

```bash
export ANTHROPIC_API_KEY='your-key'
export LANGCHAIN_API_KEY='your-key'

# Terminal 1
uv run langgraph_plugin/functional_api/langsmith_tracing/run_worker.py

# Terminal 2
uv run langgraph_plugin/functional_api/langsmith_tracing/run_workflow.py
```

Traces will appear in your [LangSmith](https://smith.langchain.com/) dashboard.

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `@traceable` chat task, `@entrypoint`, and `ChatFunctionalWorkflow` |
| `run_worker.py` | Creates client with `LangSmithPlugin`, worker with `LangGraphPlugin` |
| `run_workflow.py` | Creates client with `LangSmithPlugin`, executes workflow |
