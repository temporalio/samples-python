# Human-in-the-Loop Chatbot (Functional API)

Same pattern as the Graph API version, but using `@task` and `@entrypoint` decorators for an imperative programming style.

## What This Sample Demonstrates

- Using `interrupt()` inside a `@task` to pause for human input
- Temporal signals and queries for asynchronous human feedback
- Resuming with `Command(resume=...)` via the v2 API
- Setting a checkpointer on the entrypoint for interrupt/resume support

## How It Works

1. The `generate_draft` task produces a draft response.
2. The `request_human_review` task calls `interrupt(draft)`, pausing the entrypoint.
3. The workflow stores the draft and waits for a signal.
4. After receiving feedback, the entrypoint resumes and returns the result.

## Running the Sample

Prerequisites: `uv sync --group langgraph` and a running Temporal dev server.

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
