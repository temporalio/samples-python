# Continue-as-New with Caching (Functional API)

Same pattern as the Graph API version, using `@task` and `@entrypoint` decorators.

## What This Sample Demonstrates

- Task result caching across continue-as-new boundaries with `get_cache()`
- Restoring cached results with `entrypoint(name, cache=...)`
- Each `@task` executes exactly once despite multiple workflow invocations

## How It Works

1. Three tasks run sequentially: `extract` (x2) -> `transform` (+50) -> `load` (x3).
2. After the first invocation, the workflow continues-as-new with the cache.
3. On subsequent invocations, all tasks return cached results instantly.
4. Input 10 -> 20 -> 70 -> 210.

## Running the Sample

Prerequisites: `uv sync --group langgraph` and a running Temporal dev server.

```bash
# Terminal 1
uv run langgraph_plugin/functional_api/continue_as_new/run_worker.py

# Terminal 2
uv run langgraph_plugin/functional_api/continue_as_new/run_workflow.py
```

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `@task` functions, `@entrypoint`, `PipelineInput`, and `PipelineFunctionalWorkflow` |
| `run_worker.py` | Registers tasks and entrypoint with `LangGraphPlugin`, starts worker |
| `run_workflow.py` | Executes the pipeline workflow and prints the result |
