# Subagents

Durability propagates across the entire agent tree with **no per-sub-agent
wiring**. A coordinator agent built with `create_deep_agent(..., subagents=[...])`
delegates to its sub-agents through the built-in `task` tool. Deep Agents builds
each sub-agent as a separate graph, but they inherit the parent's `model` object
by default — so because the plugin makes that one model object durable, every
sub-agent's model call also becomes a `deepagents.invoke_model` activity
automatically.

In this sample the coordinator delegates deep investigation to a `researcher`
sub-agent and then synthesizes a final answer. Both the coordinator's and the
researcher's LLM calls run as durable activities.

## What This Sample Demonstrates

- `create_deep_agent(subagents=[...])` with a delegated `researcher`
- Durability inheritance: sub-agent model calls route through activities with no
  extra wiring

## Running the Sample

Prerequisites: Python >= 3.11 with the [suite setup](../README.md#prerequisites)
applied (interim plugin install), an `ANTHROPIC_API_KEY` in your
environment, and a running Temporal dev server (`temporal server start-dev`).

> The experimental plugin is not in the `deepagents` group — install it as shown
> in the [suite README](../README.md#prerequisites) and run with `--no-sync`, or
> a bare `uv run`/`uv sync` re-syncs the environment and uninstalls it.

```bash
# Terminal 1
uv run --no-sync deepagents_plugin/subagents/run_worker.py

# Terminal 2
uv run --no-sync deepagents_plugin/subagents/run_workflow.py
```

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `SubagentsWorkflow`: a coordinator with a `researcher` sub-agent |
| `run_worker.py` | Adds `DeepAgentsPlugin`, starts the worker |
| `run_workflow.py` | Executes the workflow and prints the result |
