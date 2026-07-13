# Tools — Temporal Activities as ADK Tools

A weather agent whose `get_weather` Temporal activity is wrapped as an ADK tool
with `activity_tool(...)`. The model decides to call the tool; the tool runs as
its own Temporal activity — retryable and observable — rather than inline in the
workflow. This demonstrates the activity boundary for tool calls.

Before running, review the [prerequisites in the suite README](../README.md)
(Temporal dev server, `uv sync --group google-adk`, and
`export GOOGLE_API_KEY=...`).

## Running

Start the worker in one terminal:

```bash
uv run python -m google_adk_agents.tools.run_worker
```

Then start the workflow in another terminal:

```bash
uv run python -m google_adk_agents.tools.run_weather_workflow
```

## What to expect

The starter asks "What is the weather in New York?" and prints the agent's
answer, which incorporates the (canned) weather the tool returned.

## In the Temporal UI

Open the workflow `google-adk-agents-tools-workflow-id`. The history shows the
model deciding to call the tool, then a `get_weather` activity for the tool
call, then a second `invoke_model` activity where the model turns the tool
result into a final answer. Each model turn and each tool call is its own
activity.
