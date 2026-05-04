# Human-in-the-Loop Chatbot (Functional API)

Demonstrates pausing an entrypoint with LangGraph's `interrupt()` and waiting indefinitely for human review with Temporal's `workflow.wait_condition()`. A Temporal signal delivers the human's feedback; a Temporal query exposes the pending draft to UIs.

## What This Sample Demonstrates

- `workflow.wait_condition()` to block the Workflow until human input arrives — for as long as it takes, with no polling and no timeout
- `interrupt()` inside a `@task` to pause the entrypoint at the review point
- Temporal **signals** to deliver human feedback and **queries** to expose the pending draft
- Resuming with `Command(resume=...)` via the v2 API
- Setting a checkpointer on the entrypoint for interrupt/resume support

## How It Works

1. The `generate_draft` task produces a draft response.
2. The `request_human_review` task calls `interrupt(draft)`, pausing the entrypoint.
3. The Workflow stores the draft (visible via the query) and calls `workflow.wait_condition()` — blocking durably until the signal sets `_human_input`. This can wait indefinitely; Temporal persists the state.
4. After the signal arrives, the entrypoint resumes with `Command(resume=...)` and returns the final response.

## Running the Sample

Prerequisites: `uv sync --group langgraph` and a running Temporal dev server (`temporal server start-dev`).

```bash
# Terminal 1
uv run langgraph_plugin/functional_api/human_in_the_loop/run_worker.py

# Terminal 2
uv run langgraph_plugin/functional_api/human_in_the_loop/run_workflow.py
```

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `@task` functions, `@entrypoint`, and `ChatbotFunctionalWorkflow` |
| `run_worker.py` | Registers tasks and entrypoint with `LangGraphPlugin`, starts worker |
| `run_workflow.py` | Starts workflow, polls draft via query, sends approval via signal |
