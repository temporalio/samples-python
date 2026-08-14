# Human in the Loop

Pause a Deep Agent for human approval before it runs a guarded tool, then resume
it with the human's decision — using the **native LangGraph interrupt protocol**
(the plugin adds no shim of its own).

`create_deep_agent(..., interrupt_on={"book_trip": True})` plus an in-workflow
`InMemorySaver` checkpointer make the agent pause before calling `book_trip`.
With a checkpointer configured, `ainvoke` *returns* the pending approval under
the SDK-native `__interrupt__` key rather than raising. Because the loop runs in
the workflow, the pause surfaces in workflow code, where it is mapped to
Temporal messaging:

- a **`@workflow.query`** (`pending_approval`) exposes the pending prompt;
- a **`@workflow.update`** (`resume`) feeds the decision back via
  `Command(resume={"decisions": [{"type": decision}]})`.

The `InMemorySaver` is replay-safe (its state is workflow memory rehydrated by
replay); the `thread_id` is the workflow id.

For clarity this sample handles a single interrupt. A production workflow would
loop — re-checking `__interrupt__` after each resume — since the model may
request another guarded tool call.

## What This Sample Demonstrates

- `interrupt_on` + an in-workflow `InMemorySaver` checkpointer
- Reading the native `__interrupt__` return value in workflow code
- Mapping the pause to a Temporal Query and the resume to a Temporal Update

## Running the Sample

Prerequisites: Python >= 3.11 with the [suite setup](../README.md#prerequisites)
applied (interim plugin install), an `ANTHROPIC_API_KEY` in your
environment, and a running Temporal dev server (`temporal server start-dev`).

> The experimental plugin is not in the `deepagents` group — install it as shown
> in the [suite README](../README.md#prerequisites) and run with `--no-sync`, or
> a bare `uv run`/`uv sync` re-syncs the environment and uninstalls it.

```bash
# Terminal 1
uv run --no-sync deepagents_plugin/human_in_the_loop/run_worker.py

# Terminal 2
uv run --no-sync deepagents_plugin/human_in_the_loop/run_workflow.py
```

The starter polls the query until the agent pauses, prints the approval prompt,
sends an `approve` decision via the update, and prints the final result.

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `HumanInTheLoopAgent` with `interrupt_on`, a Query, and an Update |
| `run_worker.py` | Adds `DeepAgentsPlugin`, starts the worker |
| `run_workflow.py` | Starts the workflow, polls the query, sends the resume update |
