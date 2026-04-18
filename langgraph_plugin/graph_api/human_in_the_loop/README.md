# Human-in-the-Loop Chatbot (Graph API)

Demonstrates using LangGraph's `interrupt()` to pause a workflow for human review, combined with Temporal signals and queries for asynchronous feedback.

## What This Sample Demonstrates

- Pausing a graph mid-execution with `interrupt()` to wait for human input
- Using Temporal **signals** to deliver human feedback to a running workflow
- Using Temporal **queries** to expose pending review state to external UIs
- Resuming the graph with `Command(resume=...)` after receiving input

## How It Works

1. The workflow starts and the `generate_draft` node produces a response.
2. The `human_review` node calls `interrupt(draft)`, pausing execution.
3. The workflow exposes the draft via a query and waits for a signal.
4. An external process (UI, CLI, etc.) queries the draft and sends approval via signal.
5. The graph resumes — `interrupt()` returns the signal value and the node completes.

## Running the Sample

Prerequisites: `uv sync --group langgraph` and a running Temporal dev server.

```bash
# Terminal 1: start the worker
uv run langgraph_plugin/graph_api/human_in_the_loop/run_worker.py

# Terminal 2: start the workflow (polls for draft, then auto-approves)
uv run langgraph_plugin/graph_api/human_in_the_loop/run_workflow.py
```

## Files

| File | Description |
|------|-------------|
| `workflow.py` | Graph node functions, graph definition, and `ChatbotWorkflow` definition |
| `run_worker.py` | Builds graph, registers with `LangGraphPlugin`, starts worker |
| `run_workflow.py` | Starts workflow, polls draft via query, sends approval via signal |
