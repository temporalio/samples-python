# React Agent (tool-calling loop)

A Deep Agent that loops over tool calls until it produces a final answer. This
sample demonstrates the **explicit Workflow-vs-Activity choice per tool** — the
core decision when making an agent durable:

- **`activity_as_tool`** exposes an existing Temporal activity (`get_weather`)
  as a Deep Agents tool. The tool advertises the activity's argument schema to
  the model and dispatches to the activity via `workflow.execute_activity`.
- **`tool_as_activity`** wraps a LangChain tool (`web_search`) whose body does
  I/O so its execution runs as a `deepagents.invoke_tool` activity instead of
  inline in the workflow.

The agent is built with `create_temporal_deep_agent(..., activity_options=...)`
— the recommended way to scope model-call activity options (timeouts, retry
policy) to one agent instead of relying on the plugin-wide default. Every model
turn and every tool call is a durable activity.

## What This Sample Demonstrates

- `create_temporal_deep_agent` with per-agent `activity_options` for model calls
- `activity_as_tool` for an existing `@activity.defn`
- `tool_as_activity` for a LangChain tool that does I/O
- Registering the user activity on the worker alongside the plugin's activities

## Running the Sample

Prerequisites: Python >= 3.11 with the [suite setup](../README.md#prerequisites)
applied (interim plugin install), an `ANTHROPIC_API_KEY` in your
environment, and a running Temporal dev server (`temporal server start-dev`).

> The experimental plugin is not in the `deepagents` group — install it as shown
> in the [suite README](../README.md#prerequisites) and run with `--no-sync`, or
> a bare `uv run`/`uv sync` re-syncs the environment and uninstalls it.

```bash
# Terminal 1
uv run --no-sync deepagents_plugin/react_agent/run_worker.py

# Terminal 2
uv run --no-sync deepagents_plugin/react_agent/run_workflow.py
```

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `get_weather` activity, `web_search` tool, and the `ReactAgent` workflow |
| `run_worker.py` | Adds `DeepAgentsPlugin`, registers `get_weather`, starts the worker |
| `run_workflow.py` | Executes the workflow and prints the result |
