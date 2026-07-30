# Agent Patterns — Multi-Agent Coordinator

A coordinator `LlmAgent` with `sub_agents=[researcher, writer]`. Each agent uses
its own `TemporalModel` with an `ActivityConfig(summary=...)`, so the agents
show up as named activities in workflow history. This demonstrates ADK's
built-in `transfer_to_agent` handoff running durably, with per-agent activity
summaries.

Before running, review the [prerequisites in the suite README](../README.md)
(Temporal dev server, `uv sync --group google-adk`, and
`export GOOGLE_API_KEY=...`).

## Running

Start the worker in one terminal:

```bash
uv run python -m google_adk_agents.agent_patterns.run_worker
```

Then start the workflow in another terminal:

```bash
uv run python -m google_adk_agents.agent_patterns.run_multi_agent_workflow
```

## What to expect

The starter asks for a haiku about the ocean. The coordinator delegates to the
researcher and then the writer; the starter prints the final haiku.

## In the Temporal UI

Open the workflow `google-adk-agents-agent-patterns-workflow-id`. The
`invoke_model` activities are labeled with their agent summaries —
"Coordinator Agent", "Researcher Agent", "Writer Agent" — so you can follow the
handoffs between agents directly in the history.
