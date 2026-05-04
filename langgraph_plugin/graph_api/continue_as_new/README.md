# Continue-as-New with Caching (Graph API)

Demonstrates combining Temporal's continue-as-new with the LangGraph plugin's task result cache to avoid re-executing completed graph nodes across workflow boundaries.

## What This Sample Demonstrates

- Using `workflow.continue_as_new()` to reset event history for long-running pipelines
- Capturing node results with `cache()` before continuing
- Restoring cached results with `temporal_graph(name, cache=...)` so completed nodes are skipped
- Each node executes exactly once despite multiple workflow invocations

## How It Works

1. A 3-stage pipeline runs: `double` (x2) -> `add_50` (+50) -> `triple` (x3).
2. After the first invocation, the workflow continues-as-new with the cached results.
3. On the second and third invocations, all three nodes return cached results instantly.
4. The final result is returned: input 10 -> 20 -> 70 -> 210.

## Running the Sample

Prerequisites: `uv sync --group langgraph` and a running Temporal dev server (`temporal server start-dev`).

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
| `run_worker.py` | Builds graph, registers with `LangGraphPlugin`, starts Worker |
| `run_workflow.py` | Executes the pipeline Workflow and prints the result |
