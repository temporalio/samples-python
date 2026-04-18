# Continue-as-New with Caching (Graph API)

Demonstrates Temporal's continue-as-new with LangGraph's task result caching to avoid re-executing completed graph nodes across workflow boundaries.

## What This Sample Demonstrates

- Using `workflow.continue_as_new()` to reset event history for long-running pipelines
- Capturing task results with `get_cache()` before continuing
- Restoring cached results with `graph(name, cache=...)` so completed nodes are skipped
- Each node executes exactly once despite multiple workflow invocations

## How It Works

1. A 3-stage pipeline runs: `extract` (x2) -> `transform` (+50) -> `load` (x3).
2. After the first invocation, the workflow continues-as-new with the cached results.
3. On the second and third invocations, all three nodes return cached results instantly.
4. The final result is returned: input 10 -> 20 -> 70 -> 210.

## Running the Sample

Prerequisites: `uv sync --group langgraph` and a running Temporal dev server.

```bash
# Terminal 1
uv run langgraph_plugin/graph_api/continue_as_new/run_worker.py

# Terminal 2
uv run langgraph_plugin/graph_api/continue_as_new/run_workflow.py
```

## Files

| File | Description |
|------|-------------|
| `workflow.py` | Pipeline node functions, graph definition, `PipelineInput`, and `PipelineWorkflow` |
| `run_worker.py` | Builds graph, registers with `LangGraphPlugin`, starts worker |
| `run_workflow.py` | Executes the pipeline workflow and prints the result |
