# Hello World (Graph API)

The simplest possible LangGraph + Temporal sample: a single-node graph that processes a query string.

## What This Sample Demonstrates

- Defining a `StateGraph` with a single node
- Wrapping it with `LangGraphPlugin` so the node runs as a Temporal activity
- Invoking the graph from a Temporal workflow

## Running the Sample

Prerequisites: `uv sync --group langgraph` and a running Temporal dev server.

```bash
# Terminal 1
uv run langgraph_plugin/graph_api/hello_world/run_worker.py

# Terminal 2
uv run langgraph_plugin/graph_api/hello_world/run_workflow.py
```

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `process_query` node, graph definition and `HelloWorldWorkflow` |
| `run_worker.py` | Registers graph with `LangGraphPlugin`, starts worker |
| `run_workflow.py` | Executes the workflow and prints the result |
