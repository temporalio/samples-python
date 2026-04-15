# Hello World (Functional API)

The simplest possible LangGraph Functional API + Temporal sample: a single `@task` called from an `@entrypoint`.

## What This Sample Demonstrates

- Defining a `@task` and `@entrypoint`
- Wrapping them with `LangGraphPlugin` so the task runs as a Temporal activity
- Invoking the entrypoint from a Temporal workflow

## Running the Sample

Prerequisites: `uv sync --group langgraph` and a running Temporal dev server.

```bash
# Terminal 1
uv run langgraph_plugin/functional_api/hello_world/run_worker.py

# Terminal 2
uv run langgraph_plugin/functional_api/hello_world/run_workflow.py
```

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `process_query` task, `hello_entrypoint`, and `HelloWorldFunctionalWorkflow` |
| `run_worker.py` | Registers task and entrypoint with `LangGraphPlugin`, starts worker |
| `run_workflow.py` | Executes the workflow and prints the result |
