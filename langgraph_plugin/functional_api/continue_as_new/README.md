# Continue-as-New with Caching (Functional API)

Demonstrates combining Temporal's continue-as-new with the LangGraph plugin's task result cache to avoid re-executing completed `@task` functions across workflow boundaries.

## What This Sample Demonstrates

- Task result caching across continue-as-new boundaries with `cache()`
- Restoring cached results with `entrypoint(name, cache=...)`
- Each `@task` executes exactly once despite multiple workflow invocations

## How It Works

1. Three tasks run sequentially: `double` (x2) -> `add_50` (+50) -> `triple` (x3).
2. After the first invocation, the workflow continues-as-new with the cache.
3. On subsequent invocations, all tasks return cached results instantly.
4. Input 10 -> 20 -> 70 -> 210.

## Running the Sample

Prerequisites: `uv sync --group langgraph` and a running Temporal dev server (`temporal server start-dev`).

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
| `run_worker.py` | Registers tasks and entrypoint with `LangGraphPlugin`, starts Worker |
| `run_workflow.py` | Executes the pipeline Workflow and prints the result |
