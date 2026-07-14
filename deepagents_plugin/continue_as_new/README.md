# Continue as New

A long-running research agent whose conversation could outgrow Temporal's
workflow-history limit. `run_deep_agent(..., continue_as_new_after=N)` keeps the
run bounded: once history passes `N` events and the agent still has pending
todos, it snapshots the accumulated messages **and** the model/tool result cache
and continues into a fresh run. Completed model/tool calls are reused from the
carried cache rather than re-run.

The `@workflow.run` signature is `run(self, input, state_snapshot=None)`, where
`input` is the messages mapping and `state_snapshot` is how `run_deep_agent`
threads carried state into the continued run. On a continue-as-new the workflow
is re-invoked with `args=[input, snapshot]`, so `input` must be passed straight
into `run_deep_agent` — re-wrapping it would nest a dict where a message is
expected and corrupt the carried conversation. Durability rides on the default
in-workflow `InMemorySaver` (rehydrated by replay); a database-backed
checkpointer would do I/O from workflow code and is not replay-safe.

## What This Sample Demonstrates

- `run_deep_agent(agent, input, continue_as_new_after=..., state_snapshot=...)`
- The `run(self, input, state_snapshot=None)` continue-as-new contract
- Carrying both messages and the result cache across continue-as-new

## Running the Sample

Prerequisites: `uv sync --group deepagents`, an `ANTHROPIC_API_KEY` in your
environment, and a running Temporal dev server (`temporal server start-dev`).

> The experimental plugin is not in the `deepagents` group — install it as shown
> in the [suite README](../README.md#prerequisites) and run with `--no-sync`, or
> a bare `uv run`/`uv sync` re-syncs the environment and uninstalls it.

```bash
# Terminal 1
uv run --no-sync deepagents_plugin/continue_as_new/run_worker.py

# Terminal 2
uv run --no-sync deepagents_plugin/continue_as_new/run_workflow.py
```

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `LongResearchAgent` driven by `run_deep_agent` with `continue_as_new_after` |
| `run_worker.py` | Adds `DeepAgentsPlugin`, starts the worker |
| `run_workflow.py` | Executes the workflow and prints the result |
