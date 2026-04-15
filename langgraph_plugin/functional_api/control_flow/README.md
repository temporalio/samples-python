# Control Flow (Functional API)

Demonstrates the Functional API's strength for complex control flow: parallel execution, sequential loops, and conditional branching — all as natural Python code.

## What This Sample Demonstrates

- **Parallel execution**: launching multiple tasks concurrently by creating futures before awaiting
- **For loops**: processing items sequentially with `for item in items`
- **If/else branching**: routing items based on classification results
- Why the Functional API is ideal for programmatic composition patterns

## How It Works

1. A batch of items is validated **in parallel** — all `validate_item` tasks launch concurrently.
2. Valid items are processed **sequentially** in a for loop.
3. Each item is classified, then routed via **if/else** to `process_urgent` or `process_normal`.
4. Results are aggregated with a `summarize` task.

## Running the Sample

Prerequisites: `uv sync --group langgraph` and a running Temporal dev server.

```bash
# Terminal 1
uv run langgraph_plugin/functional_api/control_flow/run_worker.py

# Terminal 2
uv run langgraph_plugin/functional_api/control_flow/run_workflow.py
```

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `@task` functions (validate, classify, process, summarize), `@entrypoint`, and `ControlFlowWorkflow` |
| `run_worker.py` | Registers tasks and entrypoint with `LangGraphPlugin`, starts worker |
| `run_workflow.py` | Sends a batch of items and prints processing results |
