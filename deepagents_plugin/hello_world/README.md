# Hello World

The simplest Deep Agents + Temporal sample: build a Deep Agent with
`create_deep_agent(...)` and invoke it once. The agent code is unchanged from a
non-Temporal program — adding `DeepAgentsPlugin()` to the client is what makes
the single LLM call run as a durable `deepagents.invoke_model` activity, with
Temporal-managed retries and timeouts.

## What This Sample Demonstrates

- Wiring `DeepAgentsPlugin` onto the client (it auto-propagates to the worker)
- Building a Deep Agent from a bare `model="anthropic:claude-sonnet-4-5"` string,
  which the plugin auto-routes through the model activity
- Driving the agent with `await agent.ainvoke(...)` from a `@workflow.defn`

## Running the Sample

Prerequisites: Python >= 3.11 with the [suite setup](../README.md#prerequisites)
applied (interim plugin install), an `ANTHROPIC_API_KEY` in your
environment, and a running Temporal dev server (`temporal server start-dev`).

> The experimental plugin is not in the `deepagents` group — install it as shown
> in the [suite README](../README.md#prerequisites) and run with `--no-sync`, or
> a bare `uv run`/`uv sync` re-syncs the environment and uninstalls it.

```bash
# Terminal 1
uv run --no-sync deepagents_plugin/hello_world/run_worker.py

# Terminal 2
uv run --no-sync deepagents_plugin/hello_world/run_workflow.py
```

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `HelloWorldAgent`: one Deep Agent, one `ainvoke` |
| `run_worker.py` | Adds `DeepAgentsPlugin` to the client, starts the worker |
| `run_workflow.py` | Executes the workflow and prints the result |
